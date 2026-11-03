"""Screen inventory only; workflow behavior and caller roles remain in contract.py."""
from myworkflow.contracts.screens import Screen, ScreenFeature, WorkflowCall
from examples.apps.purchase import contract as c


def call(workflow, binding, trigger):
    return WorkflowCall(c.compiled.workflow(workflow).id, binding.id, trigger.id)


SCREENS = (
    Screen('screen.purchase_entry', '購買申請入力', (
        ScreenFeature('feature.purchase_total', '合計金額の再計算', '金額欄の値を変更する',
                      '入力値から合計金額を画面内で再計算して表示する。保存やワークフローの呼出は行わない。'),
        ScreenFeature('feature.purchase_reset', '入力のクリア', 'クリアボタンを押す',
                      '画面内の未送信の入力値を空に戻す。'),
        ScreenFeature('feature.purchase_submit', '購買申請の送信', '申請ボタンを押す',
                      '入力した申請ID・取引先・金額を購買申請受付へ渡す。',
                      call(c.PurchaseApproval, c.PurchaseApproval.submit, c.PurchaseApproval.submission)),
    )),
    Screen('screen.purchase_approval', '購買申請承認', (
        ScreenFeature('feature.purchase_approve', '承認判断の送信', '承認または却下を選び、実行ボタンを押す',
                      '対象の申請IDと承認判断を送信する。承認権限や本人確認は呼出先の契約に従う。',
                      call(c.PurchaseApproval, c.PurchaseApproval.approve, c.PurchaseApproval.approval_received)),
    )),
    Screen('screen.purchase_attachment', '見積書添付', (
        ScreenFeature('feature.purchase_file_select', '添付ファイルの選択', 'ファイル選択欄で見積書を選ぶ',
                      '選択したファイル名を画面内に表示する。この時点ではアップロードしない。'),
        ScreenFeature('feature.purchase_upload', '見積書2件の登録', 'アップロードボタンを押す',
                      '申請IDと選択した見積書2件を見積書登録へ渡す。',
                      call(c.PurchaseAttachment, c.PurchaseAttachment.upload, c.PurchaseAttachment.attachment_received)),
    )),
)
