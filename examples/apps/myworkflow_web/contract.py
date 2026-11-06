"""Workflow composition for requirements, with no runtime or deployment configuration."""

from myworkflow import binding, pipeline, trigger, workflow
from myworkflow.compiler.declarations import compile_workflows
from .definitions import (
    RoleSystem,
    RoleUser,
    ProjectQuery,
    ProjectList,
    ProjectRequest,
    Project,
    Settings,
    Template,
    ChatRequest,
    ChangeSet,
    BuildRequest,
    BuildResult,
    DisplayedVersion,
    DeletionResult,
)
from .steps import (
    list_projects,
    create_project,
    save_settings,
    manage_template,
    prepare_environment,
    apply_requirements,
    build_preview,
    show_documents,
    delete_project,
)

NOTICE = "Webアプリの要件定義用カタログです。処理本体・画面・GitHub連携・開発環境の起動は未実装です。文書の生成は実行保証を意味しません。データの内部項目・制約と未決の設計案は入力資料で管理します。"


@pipeline(
    id="web.p.browse",
    name="プロジェクト一覧の取得",
    inputs=(ProjectQuery,),
    produces=(ProjectList,),
    steps=(list_projects,),
)
def browse():
    raise NotImplementedError("Declarative composition only")


@pipeline(
    id="web.p.create",
    name="プロジェクト作成",
    inputs=(ProjectRequest,),
    produces=(Project,),
    steps=(create_project,),
)
def create():
    raise NotImplementedError("Declarative composition only")


@pipeline(
    id="web.p.delete",
    name="プロジェクト削除",
    inputs=(Project,),
    produces=(DeletionResult,),
    steps=(delete_project,),
)
def delete():
    raise NotImplementedError("Declarative composition only")


@pipeline(
    id="web.p.configure",
    name="プロジェクト設定・開発ガイドの保存",
    inputs=(Project, Settings),
    produces=(Settings,),
    steps=(save_settings,),
)
def configure():
    raise NotImplementedError("Declarative composition only")


@pipeline(
    id="web.p.template",
    name="開発ガイドテンプレート管理",
    inputs=(Template,),
    produces=(Template,),
    steps=(manage_template,),
)
def template():
    raise NotImplementedError("Declarative composition only")


@pipeline(
    id="web.p.revise",
    name="対話による要件反映",
    inputs=(ChatRequest,),
    produces=(ChangeSet, BuildRequest),
    steps=(prepare_environment, apply_requirements),
)
def revise():
    raise NotImplementedError("Declarative composition only")


@pipeline(
    id="web.p.build",
    name="文書のビルドとプレビュー",
    inputs=(BuildRequest,),
    produces=(BuildResult,),
    steps=(build_preview,),
)
def build():
    raise NotImplementedError("Declarative composition only")


@pipeline(
    id="web.p.review",
    name="プロジェクト文書の閲覧",
    inputs=(Project,),
    produces=(DisplayedVersion,),
    steps=(show_documents,),
)
def review():
    raise NotImplementedError("Declarative composition only")


@workflow(id="web.w.projects", name="プロジェクトの一覧・作成・削除")
class ProjectManagement:
    @trigger(
        id="web.t.browse",
        name="一覧を開く",
        actor=RoleUser,
        mapping=((ProjectQuery, "一覧条件"),),
    )
    class BrowseRequested:
        pass

    @binding(
        id="web.b.browse",
        pipeline=browse,
        triggers=(BrowseRequested,),
        roles=(("system", RoleSystem),),
    )
    class browse:
        pass

    @trigger(
        id="web.t.create",
        name="プロジェクトを作成する",
        actor=RoleUser,
        mapping=((ProjectRequest, "プロジェクト作成内容"),),
    )
    class CreateRequested:
        pass

    @binding(
        id="web.b.create",
        pipeline=create,
        triggers=(CreateRequested,),
        roles=(("system", RoleSystem),),
    )
    class create:
        pass

    @trigger(
        id="web.t.delete",
        name="プロジェクトを削除する",
        actor=RoleUser,
        mapping=((Project, "対象プロジェクト"),),
    )
    class DeleteRequested:
        pass

    @binding(
        id="web.b.delete",
        pipeline=delete,
        triggers=(DeleteRequested,),
        roles=(("system", RoleSystem),),
    )
    class delete:
        pass


@workflow(id="web.w.settings", name="GitHub接続と開発ガイドの設定")
class ProjectConfiguration:
    @trigger(
        id="web.t.configure",
        name="設定を保存する",
        actor=RoleUser,
        mapping=(
            (Project, "対象プロジェクト"),
            (Settings, "GitHub接続・開発ガイド設定"),
        ),
    )
    class ConfigureRequested:
        pass

    @binding(
        id="web.b.configure",
        pipeline=configure,
        triggers=(ConfigureRequested,),
        roles=(("system", RoleSystem),),
    )
    class configure:
        pass


@workflow(id="web.w.templates", name="開発ガイドテンプレート管理")
class TemplateManagement:
    @trigger(
        id="web.t.template",
        name="テンプレートを管理する",
        actor=RoleUser,
        mapping=((Template, "開発ガイドテンプレート"),),
    )
    class TemplateRequested:
        pass

    @binding(
        id="web.b.template",
        pipeline=template,
        triggers=(TemplateRequested,),
        roles=(("system", RoleSystem),),
    )
    class template:
        pass


@workflow(id="web.w.development", name="対話による要件反映と文書のビルド")
class RequirementsDevelopment:
    @trigger(
        id="web.t.revise",
        name="要件をチャットで送信する",
        actor=RoleUser,
        mapping=((ChatRequest, "会話・要件変更依頼"),),
    )
    class ReviseRequested:
        pass

    @binding(
        id="web.b.revise",
        pipeline=revise,
        triggers=(ReviseRequested,),
        roles=(("system", RoleSystem),),
    )
    class revise:
        pass

    @trigger(
        id="web.t.build",
        name="手動ビルドを実行する",
        actor=RoleUser,
        mapping=((BuildRequest, "ソース版を固定したビルド依頼"),),
    )
    class BuildRequested:
        pass

    @trigger(
        id="web.t.auto_build",
        name="要件のコード反映が完了する",
        actor=RoleSystem,
        after=revise,
        mapping=((BuildRequest, "コード反映結果のビルド依頼"),),
    )
    class AutoBuildRequested:
        pass

    @binding(
        id="web.b.build",
        pipeline=build,
        triggers=(BuildRequested, AutoBuildRequested),
        roles=(("system", RoleSystem),),
    )
    class build:
        pass


@workflow(id="web.w.documents", name="プロジェクトの業務要件を確認する")
class DocumentReview:
    @trigger(
        id="web.t.review",
        name="文書トップページを開く",
        actor=RoleUser,
        mapping=((Project, "対象プロジェクト"),),
    )
    class ReviewRequested:
        pass

    @binding(
        id="web.b.review",
        pipeline=review,
        triggers=(ReviewRequested,),
        roles=(("system", RoleSystem),),
    )
    class review:
        pass


compiled = compile_workflows(
    ProjectManagement,
    ProjectConfiguration,
    TemplateManagement,
    RequirementsDevelopment,
    DocumentReview,
    artifacts=(
        ProjectQuery,
        ProjectList,
        ProjectRequest,
        Project,
        Settings,
        Template,
        ChatRequest,
        ChangeSet,
        BuildRequest,
        BuildResult,
        DisplayedVersion,
        DeletionResult,
    ),
    roles=(RoleUser, RoleSystem),
    catalog_id="myworkflow.web",
    catalog_name="myworkflow Webアプリ",
)
CATALOG = compiled.catalog
