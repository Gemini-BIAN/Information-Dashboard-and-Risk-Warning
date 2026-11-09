"""Versioned, evidence-first phase-one contracts. No production classifier/connector."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from urllib.parse import parse_qsl

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, HttpUrl, model_validator

VERSION = "1.0.0"


def safe_public_url(value):
    if value.scheme != "https" or value.username or value.password:
        raise ValueError("Public HTTPS URL without credentials required")
    if any(
        k.casefold() in {"api_key", "access_token", "token", "secret", "password"}
        for k, _ in parse_qsl(value.query or "")
    ):
        raise ValueError("Credentials must never be stored in public contracts")
    return value


PublicURL = Annotated[HttpUrl, AfterValidator(safe_public_url)]


def timezone_required(value):
    if value.tzinfo is None:
        raise ValueError("Timestamp requires timezone; unknown must be null, not an invented date")
    return value


Timestamp = Annotated[datetime, AfterValidator(timezone_required)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Domain(StrEnum):
    LOGISTICS = "A"
    POLICY = "B"
    CAPACITY = "C"
    COST = "D"
    DISRUPTION = "E"
    ACTION = "F"


PRIORITIES = {"A": "P0", "B": "P0", "C": "P1", "D": "P1", "E": "P1", "F": "P2"}
EVENT_KINDS = {
    "A": [
        "port_closure",
        "strike",
        "congestion_observation",
        "blank_sailing",
        "port_omission",
        "vessel_advisory",
        "schedule_change",
        "dg_transport_restriction",
        "eta_change",
    ],
    "B": [
        "battery_regulation",
        "battery_passport",
        "carbon_footprint",
        "dangerous_goods_rule",
        "customs",
        "tariff",
        "anti_dumping",
        "origin_rule",
        "sanction",
        "export_control",
    ],
    "C": [
        "facility_planned",
        "construction",
        "capacity_expansion",
        "production_start",
        "production_delay",
        "facility_shutdown",
    ],
    "D": ["fuel_price", "bunker_price", "freight_index", "surcharge", "rate_validity"],
    "E": ["security_event", "canal_restriction", "natural_hazard", "energy_disruption", "linked_strike"],
    "F": ["potential_impact", "verification_task", "recommended_action"],
}


class RegistrySource(StrictModel):
    source_id: str = Field(pattern=r"^[a-z][a-z0-9-]+$")
    source_name: str
    organization_id: str
    organization_group: str
    source_type: Literal["official", "secondary"]
    primary_domain: Domain
    implementation_priority: Literal["P0", "P1", "P2"]
    regions: list[str]
    url: PublicURL
    proposed_method: Literal["html_metadata", "rss_metadata", "dataset_reference", "link_only"]
    article_pattern: str | None = None
    terms_url: PublicURL | None = None
    reuse_permission: Literal["unknown", "prohibited", "conditional"] = "unknown"
    reuse_notes: str
    legal_evidence_ref: str | None = None
    suggested_poll_hours: int | None = Field(default=None, ge=1)
    status: Literal["PASS", "PARTIAL", "BLOCKED", "NOT TESTED"] = "NOT TESTED"
    last_verified_at: Timestamp | None = None
    audit_ref: str | None = None
    known_restriction: str | None = None
    baseline_only: bool = False

    @model_validator(mode="after")
    def priority_is_not_severity(self):
        if self.implementation_priority != PRIORITIES[self.primary_domain]:
            raise ValueError("Implementation priority must match domain, not event severity")
        if self.reuse_permission == "prohibited" and self.proposed_method != "link_only":
            raise ValueError("Prohibited reuse must remain link_only")
        return self


class SourceRegistry(StrictModel):
    schema_version: Literal["1.0.0"] = VERSION
    scope: Literal["phase_one_audit_only"] = "phase_one_audit_only"
    sources: list[RegistrySource] = Field(min_length=15, max_length=25)

    @model_validator(mode="after")
    def unique_sources(self):
        ids = [s.source_id for s in self.sources]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate source_id")
        return self


class Relevance(StrictModel):
    decision: Literal["relevant", "possibly_relevant", "excluded", "unknown"] = "unknown"
    reason_codes: list[str] = Field(min_length=1)
    reasons_zh: list[str] = Field(min_length=1)
    explicit_supply_chain_link: bool = False
    assessed_at: Timestamp | None = None


class EvidenceSnippet(StrictModel):
    evidence_id: str
    source_url: PublicURL
    quote: str = Field(min_length=1, max_length=3000)
    locator: str = Field(min_length=1)
    raw_revision_id: str | None = None
    raw_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    capture_mode: Literal["live", "demo", "fixture"]
    precision_note: str | None = None


class FactualStatement(StrictModel):
    text_zh: str
    evidence_ids: list[str] = Field(min_length=1)


class Inference(StrictModel):
    text_zh: str
    evidence_ids: list[str] = Field(min_length=1)
    certainty: Literal["hypothesis"] = "hypothesis"


class SuggestedAction(StrictModel):
    text_zh: str
    evidence_ids: list[str] = Field(min_length=1)
    status: Literal["proposed", "in_review", "done", "dismissed"] = "proposed"
    verification_question: str


class Applicability(StrictModel):
    status: Literal["proposal", "adopted", "effective", "repealed", "unknown"] = "unknown"
    legal_identifier: str | None = None
    jurisdictions: list[str] = Field(default_factory=list)
    products_in_scope: list[str] = Field(default_factory=list)
    products_out_of_scope: list[str] = Field(default_factory=list)
    electrolyte_applicability: Literal["direct", "indirect", "not_applicable", "unknown"] = "unknown"
    effective_at: Timestamp | None = None
    expiry_at: Timestamp | None = None
    repeal_at: Timestamp | None = None
    date_precision: Literal["instant", "date_only", "unknown"] = "unknown"
    evidence_ids: list[str] = Field(default_factory=list)
    applicability_note_zh: str

    @model_validator(mode="after")
    def require_status_and_scope_evidence(self):
        if (
            self.status != "unknown" or self.electrolyte_applicability != "unknown"
        ) and not self.evidence_ids:
            raise ValueError("Legal status/applicability requires evidence, not date comparison")
        return self


class GenericAsset(StrictModel):
    asset_type: Literal["country", "port", "lane", "facility", "product"]
    label: str
    public_generic_only: Literal[True] = True
    association: Literal["explicit", "candidate_unverified"] = "candidate_unverified"
    evidence_ids: list[str] = Field(min_length=1)


class IntelligenceRecord(StrictModel):
    schema_version: Literal["1.0.0"] = VERSION
    record_id: str
    data_mode: Literal["live", "demo", "fixture"]
    source_id: str
    source_name: str
    source_type: Literal["official", "secondary"]
    organization_id: str
    canonical_url: PublicURL
    permitted_method: Literal[
        "html_metadata", "rss_metadata", "dataset_reference", "link_only", "licensed_text"
    ]
    license_name: str | None = None
    reuse_audit_ref: str
    original_title: str
    title_zh: str | None = None
    source_published_at: Timestamp | None = None
    publication_precision: Literal["instant", "date_only", "unknown"] = "unknown"
    event_occurred_at: Timestamp | None = None
    fetched_at: Timestamp
    last_verified_at: Timestamp
    countries: list[str] = Field(default_factory=list)
    ports: list[str] = Field(default_factory=list)
    routes: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    primary_domain: Domain | None = None
    secondary_tags: list[str] = Field(default_factory=list)
    implementation_priority: Literal["P0", "P1", "P2"] | None = None
    event_kind: str = "unknown"
    event_lifecycle: Literal["announced", "active", "resolved", "cancelled", "unknown"] = "unknown"
    content_severity: Literal["high", "medium", "low", "unknown"] = "unknown"
    severity_reasons: list[str] = Field(min_length=1)
    operational_state: Literal["confirmed_current_disruption", "announced_only", "resolved", "unknown"] = (
        "unknown"
    )
    evidence_confidence: Literal[
        "unreviewed", "source_checked", "human_confirmed", "contradictory", "unknown"
    ] = "unreviewed"
    review_status: Literal["pending", "confirmed", "rejected"] = "pending"
    currentness_checked_at: Timestamp | None = None
    business_relevance: Relevance
    evidence_snippets: list[EvidenceSnippet] = Field(default_factory=list)
    factual_summary_zh: list[FactualStatement] = Field(default_factory=list)
    hypotheses: list[Inference] = Field(default_factory=list)
    potential_impacts: list[Inference] = Field(default_factory=list)
    suggested_checks_actions: list[SuggestedAction] = Field(default_factory=list)
    generic_assets: list[GenericAsset] = Field(default_factory=list)
    applicability: Applicability | None = None
    status: Literal["metadata_only", "pending_analysis", "analyzed", "reviewed", "excluded"] = "metadata_only"
    dedup_key: str
    update_version: int = Field(ge=1)
    previous_record_ref: str | None = None
    quality_flags: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def evidence_and_state_integrity(self):
        if self.primary_domain is None:
            if self.event_kind != "unknown" or self.implementation_priority is not None:
                raise ValueError("Unclassified record must not invent event kind or priority")
        elif self.event_kind != "unknown" and self.event_kind not in EVENT_KINDS[self.primary_domain]:
            raise ValueError("Event kind does not belong to primary domain")
        if self.primary_domain and self.implementation_priority != PRIORITIES[self.primary_domain]:
            raise ValueError("Implementation priority must match domain")
        ids = [e.evidence_id for e in self.evidence_snippets]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate evidence_id")
        referenced = []
        for item in (
            self.factual_summary_zh
            + self.hypotheses
            + self.potential_impacts
            + self.suggested_checks_actions
            + self.generic_assets
        ):
            referenced.extend(item.evidence_ids)
        if self.applicability:
            referenced.extend(self.applicability.evidence_ids)
        if set(referenced) - set(ids):
            raise ValueError("Unknown evidence pointer")
        if any(e.capture_mode != self.data_mode for e in self.evidence_snippets):
            raise ValueError("Live/Demo/Fixture evidence cannot be mixed")
        if self.permitted_method == "link_only" and self.evidence_snippets:
            raise ValueError("link_only cannot carry extracted text")
        if self.operational_state == "confirmed_current_disruption":
            if not (
                self.primary_domain == "A"
                and self.event_lifecycle == "active"
                and self.review_status == "confirmed"
                and self.evidence_confidence == "human_confirmed"
                and self.currentness_checked_at
                and ids
            ):
                raise ValueError(
                    "Current confirmed disruption needs independent lifecycle/review/currentness evidence"
                )
        if (
            self.primary_domain == "E"
            and self.business_relevance.decision == "relevant"
            and not self.business_relevance.explicit_supply_chain_link
        ):
            raise ValueError("Geopolitical/environmental relevance needs explicit supply-chain linkage")
        if (
            self.applicability
            and self.applicability.status == "repealed"
            and self.operational_state == "confirmed_current_disruption"
        ):
            raise ValueError("Repealed policy cannot establish current port disruption")
        return self
