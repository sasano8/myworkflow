"""Purchase SQL and transaction boundaries, independent of fault injection."""


class PurchaseRepository:
    def __init__(self, database):
        self.database = database

    def connect(self):
        return self.database.connect()

    def after_order_insert(self):
        pass

    def application(self, identity):
        with self.connect() as db:
            row = db.execute(
                "SELECT owner,vendor,amount,status FROM applications WHERE id=?",
                (identity,),
            ).fetchone()
        if row is None:
            raise ValueError("Unknown application")
        return dict(zip(("owner", "vendor", "amount", "status"), row))

    def submit(self, identity, actor, vendor, amount):
        if amount <= 0 or not vendor.strip():
            raise ValueError("Positive amount and vendor are required")
        with self.connect() as db:
            db.execute(
                "INSERT INTO applications VALUES (?,?,?,?,?)",
                (identity, actor, vendor, amount, "waiting-approval"),
            )

    def check_upload(self, identity, actor):
        a = self.application(identity)
        if a["owner"] != actor:
            raise PermissionError("Only the applicant can attach quotations")
        if a["status"] != "waiting-approval":
            raise ValueError("Attachments require waiting-approval state")

    def decide(self, identity, actor, approved):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT owner,status FROM applications WHERE id=?", (identity,)
            ).fetchone()
            if row is None or row[1] != "waiting-approval":
                raise ValueError("Application is not awaiting approval")
            if row[0] == actor:
                raise PermissionError("Applicant cannot approve their own application")
            status = "approved" if approved else "rejected"
            db.execute(
                "UPDATE applications SET status=? WHERE id=?", (status, identity)
            )
            return status

    def eligible(self, identity):
        a = self.application(identity)
        with self.connect() as db:
            count = db.execute(
                "SELECT count(*) FROM attachments WHERE application_id=?", (identity,)
            ).fetchone()[0]
            existing = db.execute(
                "SELECT count(*) FROM orders WHERE application_id=?", (identity,)
            ).fetchone()[0]
        return a["status"] == "approved" and count == 2 and existing == 0

    def confirm(self, identity):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            a = db.execute(
                "SELECT status FROM applications WHERE id=?", (identity,)
            ).fetchone()
            count = db.execute(
                "SELECT count(*) FROM attachments WHERE application_id=?", (identity,)
            ).fetchone()[0]
            if a is None or a[0] != "approved" or count != 2:
                raise ValueError("Order conditions are not satisfied")
            order_id = f"order-{identity}"
            db.execute("INSERT INTO orders VALUES (?,?)", (order_id, identity))
            self.after_order_insert()
            db.execute(
                "UPDATE applications SET status=? WHERE id=?", ("confirmed", identity)
            )
            return order_id

    def register_attachments(self, identity, run_id):
        with self.connect() as db:
            for slot in ("A", "B"):
                row = db.execute(
                    "SELECT key FROM intents WHERE run_id=? AND slot=? AND state=?",
                    (run_id, slot, "stored"),
                ).fetchone()
                if row is None:
                    raise ValueError("Missing object intent")
                db.execute(
                    "INSERT INTO attachments VALUES (?,?,?,?)",
                    (identity, run_id, slot, row[0]),
                )
