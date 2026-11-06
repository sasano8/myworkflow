"""Roles and data outlines; payload fields and value constraints remain undecided."""

from myworkflow import role, artifact


@role(id="web.role.user", name="プロジェクトの利用者", display_name="利用者")
class RoleUser:
    pass


@role(id="web.role.system", name="myworkflow Webアプリ", display_name="システム")
class RoleSystem:
    pass


@artifact(id="web.a.project_query", name="一覧条件", key="project_query", type="dict")
class ProjectQuery:
    pass


@artifact(
    id="web.a.project_list", name="プロジェクト一覧", key="project_list", type="dict"
)
class ProjectList:
    pass


@artifact(
    id="web.a.project_request",
    name="プロジェクト作成内容",
    key="project_request",
    type="dict",
)
class ProjectRequest:
    pass


@artifact(id="web.a.project", name="対象プロジェクト", key="project", type="dict")
class Project:
    pass


@artifact(
    id="web.a.settings", name="GitHub接続・開発ガイド設定", key="settings", type="dict"
)
class Settings:
    pass


@artifact(
    id="web.a.template", name="開発ガイドテンプレート", key="template", type="dict"
)
class Template:
    pass


@artifact(
    id="web.a.chat_request", name="会話・要件変更依頼", key="chat_request", type="dict"
)
class ChatRequest:
    pass


@artifact(
    id="web.a.change_set",
    name="会話と結び付いたコード差分",
    key="change_set",
    type="dict",
)
class ChangeSet:
    pass


@artifact(
    id="web.a.build_request",
    name="ソース版を固定したビルド依頼",
    key="build_request",
    type="dict",
)
class BuildRequest:
    pass


@artifact(
    id="web.a.build_result", name="ビルド・検証結果", key="build_result", type="dict"
)
class BuildResult:
    pass


@artifact(
    id="web.a.displayed_version",
    name="最後の成功版と最新コードとの差分",
    key="displayed_version",
    type="dict",
)
class DisplayedVersion:
    pass


@artifact(
    id="web.a.deletion_result",
    name="プロジェクト削除結果",
    key="deletion_result",
    type="dict",
)
class DeletionResult:
    pass
