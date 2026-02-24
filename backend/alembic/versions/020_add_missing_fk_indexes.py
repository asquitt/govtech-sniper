"""Add missing FK indexes for query performance."""

from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # proposal_sections
    op.create_index(
        "ix_proposal_sections_assigned_to_user_id", "proposal_sections", ["assigned_to_user_id"]
    )

    # section_versions
    op.create_index("ix_section_versions_user_id", "section_versions", ["user_id"])

    # submission_packages
    op.create_index("ix_submission_packages_owner_id", "submission_packages", ["owner_id"])

    # section_evidence
    op.create_index("ix_section_evidence_chunk_id", "section_evidence", ["chunk_id"])

    # review_comments
    op.create_index("ix_review_comments_reviewer_user_id", "review_comments", ["reviewer_user_id"])
    op.create_index(
        "ix_review_comments_assigned_to_user_id", "review_comments", ["assigned_to_user_id"]
    )
    op.create_index(
        "ix_review_comments_resolved_by_user_id", "review_comments", ["resolved_by_user_id"]
    )
    op.create_index(
        "ix_review_comments_verified_by_user_id", "review_comments", ["verified_by_user_id"]
    )

    # activity_feed
    op.create_index("ix_activity_feed_section_id", "activity_feed", ["section_id"])

    # org_invitations
    op.create_index("ix_org_invitations_accepted_user_id", "org_invitations", ["accepted_user_id"])

    # workspace_invitations
    op.create_index(
        "ix_workspace_invitations_accepted_user_id", "workspace_invitations", ["accepted_user_id"]
    )

    # shared_data_permissions
    op.create_index(
        "ix_shared_data_permissions_approved_by_user_id",
        "shared_data_permissions",
        ["approved_by_user_id"],
    )

    # workspace_compliance_digest_deliveries
    op.create_index(
        "ix_ws_compliance_digest_deliveries_retry_of",
        "workspace_compliance_digest_deliveries",
        ["retry_of_delivery_id"],
    )

    # capture_activities
    op.create_index("ix_capture_activities_depends_on_id", "capture_activities", ["depends_on_id"])

    # teaming_ndas
    op.create_index("ix_teaming_ndas_rfp_id", "teaming_ndas", ["rfp_id"])

    # teaming_performance_ratings
    op.create_index(
        "ix_teaming_performance_ratings_rfp_id", "teaming_performance_ratings", ["rfp_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_teaming_performance_ratings_rfp_id", "teaming_performance_ratings")
    op.drop_index("ix_teaming_ndas_rfp_id", "teaming_ndas")
    op.drop_index("ix_capture_activities_depends_on_id", "capture_activities")
    op.drop_index(
        "ix_ws_compliance_digest_deliveries_retry_of", "workspace_compliance_digest_deliveries"
    )
    op.drop_index("ix_shared_data_permissions_approved_by_user_id", "shared_data_permissions")
    op.drop_index("ix_workspace_invitations_accepted_user_id", "workspace_invitations")
    op.drop_index("ix_org_invitations_accepted_user_id", "org_invitations")
    op.drop_index("ix_activity_feed_section_id", "activity_feed")
    op.drop_index("ix_review_comments_verified_by_user_id", "review_comments")
    op.drop_index("ix_review_comments_resolved_by_user_id", "review_comments")
    op.drop_index("ix_review_comments_assigned_to_user_id", "review_comments")
    op.drop_index("ix_review_comments_reviewer_user_id", "review_comments")
    op.drop_index("ix_section_evidence_chunk_id", "section_evidence")
    op.drop_index("ix_submission_packages_owner_id", "submission_packages")
    op.drop_index("ix_section_versions_user_id", "section_versions")
    op.drop_index("ix_proposal_sections_assigned_to_user_id", "proposal_sections")
