"""Daily report requirements and its cron entry point."""
from myworkflow import Artifact, Binding, ContractCatalog, Pipeline, Role, Step, Trigger, Workflow
from myworkflow.contracts.schedules import CronSchedule

system = Role('role.report_system', '日次レポート実行システム', 'システム')
business_date = Artifact('a.report_date', '集計対象日', 'business_date', 'str')
report = Artifact('a.report', '日次レポート', 'report', 'str')
create_report = Step('s.create_report', '日次レポートの作成',
                     '対象日をキーに日次レポートを保存する。同じ対象日の再実行でもレポートを重複作成しない。',
                     reads=(business_date.id,), writes=(report.id,))
pipeline = Pipeline('p.daily_report', '日次レポート作成', (business_date.id,), (report.id,), (create_report,))
requested = Trigger('t.daily_cron', 'cronの定期起動', ((business_date.id, 'business_date'),), actor_role_id=system.id)
placement = Binding('b.daily_report', pipeline.id, (requested,), (('system', system.id),))
workflow = Workflow('w.daily_report', '前日分の日次レポート作成', (placement,))
CATALOG = ContractCatalog((business_date, report), (pipeline,), (workflow,), (system,),
                          id='example.daily_report', name='cronによる日次レポート')
SCHEDULE = CronSchedule('cron.daily_report', '毎日6時に前日分を作成', '0 6 * * *', 'Asia/Tokyo',
                        workflow.id, placement.id, requested.id)
