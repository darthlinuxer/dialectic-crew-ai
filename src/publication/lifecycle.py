from __future__ import annotations

from enum import Enum


class PublicationLifecycle(str, Enum):
    PRE_APPROVAL_PREVIEW = "pre_approval_preview"
    AD_HOC_EXPORT = "ad_hoc_export"
    PUBLISH = "publish"
    APPROVED_PUBLICATION = "approved_publication"
