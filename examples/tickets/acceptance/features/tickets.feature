# language: ja
機能: 窓口でのチケット発行

  @scenario.tickets.issue @req.ticket.issue
  シナリオ: 受付担当がチケットを発行する
    前提 受付担当が窓口を開いている
    もし 受付番号 "T-001" を発行する
    ならば チケットが1件保存され発行結果が返る
