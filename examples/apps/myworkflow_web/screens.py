"""Screens and their workflow entry points; no UI implementation."""

from myworkflow import declaration
from myworkflow.contracts.screens import Screen, ScreenFeature, WorkflowCall
from . import contract as c
from . import requirements as r


def call(workflow, placement, trigger):
    return WorkflowCall(
        c.compiled.workflow(workflow).id,
        declaration(placement).id,
        declaration(trigger).id,
    )


def feature(requirement, event, workflow_call=None):
    spec = declaration(requirement)
    return ScreenFeature(spec.id, spec.name, event, spec.summary, workflow_call)


SCREENS = (
    Screen(
        "web.screen.projects",
        "プロジェクト一覧",
        (
            feature(
                r.ProjectListing,
                "一覧を開く",
                call(
                    c.ProjectManagement,
                    c.ProjectManagement.browse,
                    c.ProjectManagement.BrowseRequested,
                ),
            ),
            feature(
                r.ProjectCreation,
                "作成ボタンを押す",
                call(
                    c.ProjectManagement,
                    c.ProjectManagement.create,
                    c.ProjectManagement.CreateRequested,
                ),
            ),
        ),
    ),
    Screen(
        "web.screen.project",
        "プロジェクト詳細",
        (
            feature(
                r.ProjectDetails,
                "プロジェクトを選ぶ",
                call(
                    c.DocumentReview,
                    c.DocumentReview.review,
                    c.DocumentReview.ReviewRequested,
                ),
            ),
            feature(
                r.DocumentTop,
                "文書トップを開く",
                call(
                    c.DocumentReview,
                    c.DocumentReview.review,
                    c.DocumentReview.ReviewRequested,
                ),
            ),
            feature(
                r.ManualBuild,
                "ビルドボタンを押す",
                call(
                    c.RequirementsDevelopment,
                    c.RequirementsDevelopment.build,
                    c.RequirementsDevelopment.BuildRequested,
                ),
            ),
            feature(
                r.ProjectDeletion,
                "削除操作を行う",
                call(
                    c.ProjectManagement,
                    c.ProjectManagement.delete,
                    c.ProjectManagement.DeleteRequested,
                ),
            ),
        ),
    ),
    Screen(
        "web.screen.settings",
        "プロジェクト設定",
        (
            feature(r.ProjectSettings, "設定を開く"),
            feature(
                r.GitHubDestination,
                "GitHub保存先を保存する",
                call(
                    c.ProjectConfiguration,
                    c.ProjectConfiguration.configure,
                    c.ProjectConfiguration.ConfigureRequested,
                ),
            ),
        ),
    ),
    Screen(
        "web.screen.guide",
        "開発ガイド設定",
        (
            feature(r.DevelopmentGuide, "開発ガイドを開く"),
            feature(
                r.BranchStrategy,
                "push先・ブランチ戦略を保存する",
                call(
                    c.ProjectConfiguration,
                    c.ProjectConfiguration.configure,
                    c.ProjectConfiguration.ConfigureRequested,
                ),
            ),
        ),
    ),
    Screen(
        "web.screen.templates",
        "開発ガイドテンプレート管理",
        (
            feature(
                r.GuideTemplateManagement,
                "テンプレートを管理する",
                call(
                    c.TemplateManagement,
                    c.TemplateManagement.template,
                    c.TemplateManagement.TemplateRequested,
                ),
            ),
        ),
    ),
    Screen(
        "web.screen.chat",
        "チャット",
        (
            feature(
                r.RequirementChat,
                "要件を送信する",
                call(
                    c.RequirementsDevelopment,
                    c.RequirementsDevelopment.revise,
                    c.RequirementsDevelopment.ReviseRequested,
                ),
            ),
            feature(
                r.RequirementReflection,
                "要件をコードへ反映する",
                call(
                    c.RequirementsDevelopment,
                    c.RequirementsDevelopment.revise,
                    c.RequirementsDevelopment.ReviseRequested,
                ),
            ),
            feature(
                r.DevelopmentEnvironment,
                "開発環境の準備を依頼する",
                call(
                    c.RequirementsDevelopment,
                    c.RequirementsDevelopment.revise,
                    c.RequirementsDevelopment.ReviseRequested,
                ),
            ),
        ),
    ),
    Screen(
        "web.screen.documents",
        "ドキュメント",
        (
            feature(
                r.MkDocsViewing,
                "生成文書を閲覧する",
                call(
                    c.DocumentReview,
                    c.DocumentReview.review,
                    c.DocumentReview.ReviewRequested,
                ),
            ),
        ),
    ),
    Screen(
        "web.screen.build",
        "ビルド状況",
        (
            feature(
                r.AutomaticBuild,
                "要件反映完了を受ける",
                call(
                    c.RequirementsDevelopment,
                    c.RequirementsDevelopment.build,
                    c.RequirementsDevelopment.AutoBuildRequested,
                ),
            ),
        ),
    ),
)
