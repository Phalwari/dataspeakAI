"""
Extensible Domain Template Registry for DataSpeakAI.

Defines canonical domain templates (optimization templates, NOT system limitations)
for business domains (E-Commerce, SaaS, Healthcare, Logistics, Finance, etc.)
as well as a Generic / Custom fallback for unknown or arbitrary datasets.

Each domain template specifies:
- essential_variables: Business concepts (e.g. revenue, order_date) with expected semantic types and priority
- kpis: Deterministic KPI recipes computed from mapped columns
- charts: Recommended visualizations derived from mapped columns and dimensions
- filters: Recommended slicers/filters

Architecture allows adding new domain templates dynamically without modifying
the core profiling or matching engine.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class EssentialVariable:
    name: str
    display_name: str
    description: str
    required: bool
    expected_semantic_types: List[str]  # e.g. ["CURRENCY/AMOUNT", "NUMERIC_MEASURE"]
    aliases: List[str]  # common column name patterns/synonyms
    forbidden_types: List[str] = field(default_factory=lambda: ["ID", "UUID"])


@dataclass
class KpiRecipe:
    id: str
    title: str
    formula_template: str  # e.g. "SUM({revenue})" or "COUNT(DISTINCT {order_id})"
    required_variables: List[str]
    aggregation: str  # SUM, COUNT, AVG, COUNT_DISTINCT, etc.
    format: str = "number"  # currency, number, percentage
    description: str = ""


@dataclass
class ChartRecipe:
    id: str
    title: str
    chart_type: str  # line, bar, area, pie, etc.
    x_axis_var: Optional[str] = None
    y_axis_vars: List[str] = field(default_factory=list)
    breakdown_var: Optional[str] = None
    description: str = ""


@dataclass
class DomainTemplate:
    id: str
    name: str
    description: str
    is_fallback: bool = False
    essential_variables: List[EssentialVariable] = field(default_factory=list)
    kpis: List[KpiRecipe] = field(default_factory=list)
    charts: List[ChartRecipe] = field(default_factory=list)
    default_filters: List[str] = field(default_factory=list)  # variable names


# ---------------------------------------------------------------------------
# Predefined Domain Templates (Optimization Templates)
# ---------------------------------------------------------------------------

ECOMMERCE_TEMPLATE = DomainTemplate(
    id="ecommerce",
    name="E-Commerce & Retail",
    description="Online and brick-and-mortar retail with orders, products, inventory, and transactions.",
    essential_variables=[
        EssentialVariable(
            name="revenue",
            display_name="Total Revenue / Sales",
            description="Total monetary value of orders or transactions (excluding individual unit prices).",
            required=True,
            expected_semantic_types=["CURRENCY/AMOUNT", "NUMERIC_MEASURE"],
            aliases=["total_amount", "order_total", "total_price", "grand_total", "revenue", "sales_amount", "gross_sales", "net_amount", "amount", "line_total"],
        ),
        EssentialVariable(
            name="order_id",
            display_name="Order Identifier",
            description="Unique identifier for each transaction or order.",
            required=True,
            expected_semantic_types=["ID", "UUID", "TEXT", "NUMERIC_MEASURE"],
            aliases=["order_id", "order_number", "transaction_id", "invoice_id", "sale_id", "id"],
            forbidden_types=[],  # Can be ID or UUID
        ),
        EssentialVariable(
            name="order_date",
            display_name="Order Date / Timestamp",
            description="Timestamp when the purchase or transaction occurred.",
            required=True,
            expected_semantic_types=["DATETIME", "DATE"],
            aliases=["order_date", "created_at", "purchase_date", "transaction_date", "sale_date", "timestamp", "date"],
        ),
        EssentialVariable(
            name="customer_id",
            display_name="Customer / Buyer Identifier",
            description="Identifier of the purchasing user or customer.",
            required=False,
            expected_semantic_types=["ID", "UUID", "TEXT", "NUMERIC_MEASURE"],
            aliases=["customer_id", "user_id", "buyer_id", "client_id", "account_id"],
            forbidden_types=[],
        ),
        EssentialVariable(
            name="quantity",
            display_name="Quantity / Units Sold",
            description="Number of items or units ordered.",
            required=False,
            expected_semantic_types=["NUMERIC_MEASURE"],
            aliases=["quantity", "qty", "units", "items_count", "volume"],
        ),
        EssentialVariable(
            name="order_status",
            display_name="Order Status",
            description="Current fulfillment or processing stage (e.g. completed, pending, cancelled).",
            required=False,
            expected_semantic_types=["CATEGORY", "TEXT"],
            aliases=["order_status", "status", "fulfillment_status", "state"],
        ),
        EssentialVariable(
            name="category",
            display_name="Product Category / Segment",
            description="Grouping of products, items, or catalog segments.",
            required=False,
            expected_semantic_types=["CATEGORY", "TEXT"],
            aliases=["category", "product_category", "department", "genre", "type"],
        ),
    ],
    kpis=[
        KpiRecipe(
            id="total_revenue",
            title="Total Revenue",
            formula_template="SUM({revenue})",
            required_variables=["revenue"],
            aggregation="SUM",
            format="currency",
            description="Total gross sales revenue.",
        ),
        KpiRecipe(
            id="total_orders",
            title="Total Orders",
            formula_template="COUNT(DISTINCT {order_id})",
            required_variables=["order_id"],
            aggregation="COUNT_DISTINCT",
            format="number",
            description="Total count of unique orders.",
        ),
        KpiRecipe(
            id="aov",
            title="Average Order Value (AOV)",
            formula_template="AVG({revenue})",
            required_variables=["revenue"],
            aggregation="AVG",
            format="currency",
            description="Average transaction size across orders.",
        ),
        KpiRecipe(
            id="unique_customers",
            title="Active Customers",
            formula_template="COUNT(DISTINCT {customer_id})",
            required_variables=["customer_id"],
            aggregation="COUNT_DISTINCT",
            format="number",
            description="Total unique buyers.",
        ),
    ],
    charts=[
        ChartRecipe(
            id="revenue_trend",
            title="Revenue Over Time",
            chart_type="line",
            x_axis_var="order_date",
            y_axis_vars=["revenue"],
            description="Daily/Monthly sales trend line.",
        ),
        ChartRecipe(
            id="category_revenue",
            title="Sales by Category",
            chart_type="bar",
            x_axis_var="category",
            y_axis_vars=["revenue"],
            description="Total sales breakdown across product categories.",
        ),
        ChartRecipe(
            id="order_status_distribution",
            title="Orders by Status",
            chart_type="pie",
            x_axis_var="order_status",
            y_axis_vars=["order_id"],
            description="Fulfillment status proportion.",
        ),
    ],
    default_filters=["order_status", "category"],
)

SAAS_TEMPLATE = DomainTemplate(
    id="saas",
    name="SaaS & Subscription",
    description="Software-as-a-service metrics including MRR, subscriptions, retention, and churn.",
    essential_variables=[
        EssentialVariable(
            name="mrr",
            display_name="Monthly Recurring Revenue (MRR)",
            description="Monthly subscription value or recurring fee.",
            required=True,
            expected_semantic_types=["CURRENCY/AMOUNT", "NUMERIC_MEASURE"],
            aliases=["mrr", "recurring_revenue", "plan_price", "subscription_fee", "monthly_amount", "price", "amount"],
        ),
        EssentialVariable(
            name="subscription_id",
            display_name="Subscription Identifier",
            description="Unique identifier of the subscription record.",
            required=True,
            expected_semantic_types=["ID", "UUID", "TEXT", "NUMERIC_MEASURE"],
            aliases=["subscription_id", "sub_id", "membership_id", "contract_id", "id"],
            forbidden_types=[],
        ),
        EssentialVariable(
            name="subscription_date",
            display_name="Start / Renewal Date",
            description="Date when subscription was created or renewed.",
            required=True,
            expected_semantic_types=["DATETIME", "DATE"],
            aliases=["start_date", "created_at", "subscription_date", "signup_date", "renewal_date", "timestamp", "date"],
        ),
        EssentialVariable(
            name="subscription_status",
            display_name="Subscription Status",
            description="Status of account (e.g. active, churned, trial, cancelled).",
            required=False,
            expected_semantic_types=["CATEGORY", "TEXT"],
            aliases=["subscription_status", "status", "state", "account_status"],
        ),
        EssentialVariable(
            name="plan_name",
            display_name="Subscription Plan / Tier",
            description="Pricing plan tier (e.g. Starter, Pro, Enterprise).",
            required=False,
            expected_semantic_types=["CATEGORY", "TEXT"],
            aliases=["plan_name", "plan", "tier", "package", "pricing_tier"],
        ),
    ],
    kpis=[
        KpiRecipe(
            id="total_mrr",
            title="Total MRR",
            formula_template="SUM({mrr})",
            required_variables=["mrr"],
            aggregation="SUM",
            format="currency",
            description="Aggregated monthly recurring revenue.",
        ),
        KpiRecipe(
            id="active_subscriptions",
            title="Active Subscriptions",
            formula_template="COUNT(DISTINCT {subscription_id})",
            required_variables=["subscription_id"],
            aggregation="COUNT_DISTINCT",
            format="number",
            description="Total count of active subscriptions.",
        ),
        KpiRecipe(
            id="arpu",
            title="Average Revenue Per User (ARPU)",
            formula_template="AVG({mrr})",
            required_variables=["mrr"],
            aggregation="AVG",
            format="currency",
            description="Average monthly recurring fee per subscriber.",
        ),
    ],
    charts=[
        ChartRecipe(
            id="mrr_growth",
            title="MRR Growth Over Time",
            chart_type="area",
            x_axis_var="subscription_date",
            y_axis_vars=["mrr"],
            description="Recurring revenue growth trajectory.",
        ),
        ChartRecipe(
            id="plan_breakdown",
            title="Subscriptions by Plan Tier",
            chart_type="bar",
            x_axis_var="plan_name",
            y_axis_vars=["subscription_id"],
            description="Distribution of customers across subscription tiers.",
        ),
    ],
    default_filters=["subscription_status", "plan_name"],
)

HEALTHCARE_TEMPLATE = DomainTemplate(
    id="healthcare",
    name="Healthcare & Clinical",
    description="Patient encounters, admissions, diagnostics, treatments, and clinical operational metrics.",
    essential_variables=[
        EssentialVariable(
            name="encounter_id",
            display_name="Encounter / Visit Identifier",
            description="Unique identifier for patient visits or clinical encounters.",
            required=True,
            expected_semantic_types=["ID", "UUID", "TEXT", "NUMERIC_MEASURE"],
            aliases=["encounter_id", "visit_id", "admission_id", "appointment_id", "case_id", "id"],
            forbidden_types=[],
        ),
        EssentialVariable(
            name="encounter_date",
            display_name="Admission / Visit Date",
            description="Timestamp of admission, appointment, or check-in.",
            required=True,
            expected_semantic_types=["DATETIME", "DATE"],
            aliases=["admission_date", "encounter_date", "visit_date", "appointment_date", "created_at", "date"],
        ),
        EssentialVariable(
            name="patient_id",
            display_name="Patient Identifier",
            description="Anonymized or unique patient medical record identifier.",
            required=False,
            expected_semantic_types=["ID", "UUID", "TEXT", "NUMERIC_MEASURE"],
            aliases=["patient_id", "patient_mrn", "subject_id", "mrn"],
            forbidden_types=[],
        ),
        EssentialVariable(
            name="department",
            display_name="Clinical Department / Ward",
            description="Medical department, clinic, or specialty (e.g. Cardiology, ER).",
            required=False,
            expected_semantic_types=["CATEGORY", "TEXT"],
            aliases=["department", "ward", "clinic", "specialty", "unit", "division"],
        ),
        EssentialVariable(
            name="billing_amount",
            display_name="Billing / Treatment Cost",
            description="Billed charges or operational encounter cost.",
            required=False,
            expected_semantic_types=["CURRENCY/AMOUNT", "NUMERIC_MEASURE"],
            aliases=["treatmentcost", "treatment_cost", "billed_amount", "total_charge", "charge", "cost", "fee", "amount"],
        ),
        EssentialVariable(
            name="discharge_status",
            display_name="Discharge / Patient Status",
            description="Clinical status of the patient (e.g. Admitted, Discharged, Transferred).",
            required=False,
            expected_semantic_types=["CATEGORY", "TEXT"],
            aliases=["status", "discharge_status", "patient_status", "admission_type", "state"],
        ),

    ],
    kpis=[
        KpiRecipe(
            id="total_encounters",
            title="Total Patient Encounters",
            formula_template="COUNT(DISTINCT {encounter_id})",
            required_variables=["encounter_id"],
            aggregation="COUNT_DISTINCT",
            format="number",
            description="Total number of admissions or visits.",
        ),
        KpiRecipe(
            id="unique_patients",
            title="Unique Patients Served",
            formula_template="COUNT(DISTINCT {patient_id})",
            required_variables=["patient_id"],
            aggregation="COUNT_DISTINCT",
            format="number",
            description="Count of distinct patients treated.",
        ),
        KpiRecipe(
            id="avg_treatment_charge",
            title="Average Encounter Cost",
            formula_template="AVG({billing_amount})",
            required_variables=["billing_amount"],
            aggregation="AVG",
            format="currency",
            description="Average financial charge per encounter.",
        ),
    ],
    charts=[
        ChartRecipe(
            id="admissions_trend",
            title="Admissions Over Time",
            chart_type="line",
            x_axis_var="encounter_date",
            y_axis_vars=["encounter_id"],
            description="Daily/Monthly patient visit volume.",
        ),
        ChartRecipe(
            id="department_volume",
            title="Visits by Department",
            chart_type="bar",
            x_axis_var="department",
            y_axis_vars=["encounter_id"],
            description="Patient load distributed across hospital wards.",
        ),
    ],
    default_filters=["department"],
)

LOGISTICS_TEMPLATE = DomainTemplate(
    id="logistics",
    name="Logistics & Supply Chain",
    description="Shipments, deliveries, fleets, warehouse inventory, and transit logistics.",
    essential_variables=[
        EssentialVariable(
            name="shipment_id",
            display_name="Shipment / Tracking Identifier",
            description="Unique tracking number or shipment reference ID.",
            required=True,
            expected_semantic_types=["ID", "UUID", "TEXT", "NUMERIC_MEASURE"],
            aliases=["shipment_id", "tracking_number", "consignment_id", "delivery_id", "order_id", "id"],
            forbidden_types=[],
        ),
        EssentialVariable(
            name="dispatch_date",
            display_name="Dispatch / Shipping Date",
            description="Date when shipment departed origin or was booked.",
            required=True,
            expected_semantic_types=["DATETIME", "DATE"],
            aliases=["dispatch_date", "ship_date", "shipped_at", "created_at", "departure_date", "date"],
        ),
        EssentialVariable(
            name="delivery_status",
            display_name="Delivery Status",
            description="Logistics state (e.g. In Transit, Delivered, Delayed, Returned).",
            required=False,
            expected_semantic_types=["CATEGORY", "TEXT"],
            aliases=["status", "delivery_status", "shipment_status", "state"],
        ),
        EssentialVariable(
            name="shipping_cost",
            display_name="Shipping Cost / Freight Fee",
            description="Monetary cost or freight charge of delivery.",
            required=False,
            expected_semantic_types=["CURRENCY/AMOUNT", "NUMERIC_MEASURE"],
            aliases=["shipping_cost", "freight_charge", "transport_cost", "cost", "fee", "amount"],
        ),
        EssentialVariable(
            name="destination",
            display_name="Destination / Hub / Region",
            description="Target delivery city, country, or distribution center.",
            required=False,
            expected_semantic_types=["CATEGORY", "TEXT"],
            aliases=["destination", "dest_city", "country", "region", "hub", "warehouse"],
        ),
    ],
    kpis=[
        KpiRecipe(
            id="total_shipments",
            title="Total Shipments",
            formula_template="COUNT(DISTINCT {shipment_id})",
            required_variables=["shipment_id"],
            aggregation="COUNT_DISTINCT",
            format="number",
            description="Total volume of dispatched shipments.",
        ),
        KpiRecipe(
            id="total_freight_cost",
            title="Total Freight Cost",
            formula_template="SUM({shipping_cost})",
            required_variables=["shipping_cost"],
            aggregation="SUM",
            format="currency",
            description="Total expenditure on freight and shipping.",
        ),
        KpiRecipe(
            id="avg_freight_cost",
            title="Average Shipping Cost",
            formula_template="AVG({shipping_cost})",
            required_variables=["shipping_cost"],
            aggregation="AVG",
            format="currency",
            description="Average shipping cost per consignment.",
        ),
    ],
    charts=[
        ChartRecipe(
            id="shipments_over_time",
            title="Shipment Volume Trend",
            chart_type="line",
            x_axis_var="dispatch_date",
            y_axis_vars=["shipment_id"],
            description="Delivery throughput over time.",
        ),
        ChartRecipe(
            id="status_distribution",
            title="Shipments by Status",
            chart_type="pie",
            x_axis_var="delivery_status",
            y_axis_vars=["shipment_id"],
            description="Ratio of completed vs in-transit vs delayed packages.",
        ),
        ChartRecipe(
            id="destination_breakdown",
            title="Volume by Destination",
            chart_type="bar",
            x_axis_var="destination",
            y_axis_vars=["shipment_id"],
            description="Shipment counts across regional hubs.",
        ),
    ],
    default_filters=["delivery_status", "destination"],
)

FINANCE_TEMPLATE = DomainTemplate(
    id="finance",
    name="Finance & Banking",
    description="Ledger, payments, accounting entries, and banking transactions.",
    essential_variables=[
        EssentialVariable(
            name="transaction_amount",
            display_name="Transaction Amount",
            description="Monetary value of financial entry, payment, or debit/credit.",
            required=True,
            expected_semantic_types=["CURRENCY/AMOUNT", "NUMERIC_MEASURE"],
            aliases=["amount", "trans_amount", "total", "net_amount", "value", "balance"],
        ),
        EssentialVariable(
            name="transaction_id",
            display_name="Transaction Identifier",
            description="Unique reference ID for banking or accounting entry.",
            required=True,
            expected_semantic_types=["ID", "UUID", "TEXT", "NUMERIC_MEASURE"],
            aliases=["transaction_id", "txn_id", "reference_no", "entry_id", "id"],
            forbidden_types=[],
        ),
        EssentialVariable(
            name="transaction_date",
            display_name="Posting / Value Date",
            description="Timestamp of financial execution or ledger entry.",
            required=True,
            expected_semantic_types=["DATETIME", "DATE"],
            aliases=["post_date", "transaction_date", "created_at", "value_date", "date"],
        ),
        EssentialVariable(
            name="transaction_type",
            display_name="Transaction Type / Category",
            description="Credit, Debit, Transfer, Wire, Fee, or category descriptor.",
            required=False,
            expected_semantic_types=["CATEGORY", "TEXT"],
            aliases=["type", "txn_type", "category", "account_type", "status"],
        ),
    ],
    kpis=[
        KpiRecipe(
            id="total_transacted_volume",
            title="Total Transaction Volume",
            formula_template="SUM({transaction_amount})",
            required_variables=["transaction_amount"],
            aggregation="SUM",
            format="currency",
            description="Total monetary movement across entries.",
        ),
        KpiRecipe(
            id="transaction_count",
            title="Total Transactions",
            formula_template="COUNT(DISTINCT {transaction_id})",
            required_variables=["transaction_id"],
            aggregation="COUNT_DISTINCT",
            format="number",
            description="Total count of financial records processed.",
        ),
        KpiRecipe(
            id="avg_transaction_size",
            title="Average Transaction Value",
            formula_template="AVG({transaction_amount})",
            required_variables=["transaction_amount"],
            aggregation="AVG",
            format="currency",
            description="Mean monetary size per transaction.",
        ),
    ],
    charts=[
        ChartRecipe(
            id="financial_flow",
            title="Transaction Volume Over Time",
            chart_type="line",
            x_axis_var="transaction_date",
            y_axis_vars=["transaction_amount"],
            description="Chronological flow of monetary volume.",
        ),
        ChartRecipe(
            id="type_breakdown",
            title="Volume by Transaction Type",
            chart_type="bar",
            x_axis_var="transaction_type",
            y_axis_vars=["transaction_amount"],
            description="Breakdown between transaction types.",
        ),
    ],
    default_filters=["transaction_type"],
)

GENERIC_TEMPLATE = DomainTemplate(
    id="generic",
    name="Generic / Custom Dataset",
    description="Universal fallback intelligence for unknown, proprietary, or custom business databases.",
    is_fallback=True,
    essential_variables=[
        EssentialVariable(
            name="primary_measure",
            display_name="Primary Measure (Metric)",
            description="Primary numeric column to aggregate (sum, average).",
            required=False,
            expected_semantic_types=["NUMERIC_MEASURE", "CURRENCY/AMOUNT"],
            aliases=["total", "amount", "score", "value", "count", "metric", "rate", "weight"],
        ),
        EssentialVariable(
            name="primary_time_axis",
            display_name="Primary Date / Time Axis",
            description="Timestamp or date column for historical trends.",
            required=False,
            expected_semantic_types=["DATETIME", "DATE"],
            aliases=["created_at", "updated_at", "date", "timestamp", "recorded_at"],
        ),
        EssentialVariable(
            name="primary_dimension",
            display_name="Primary Dimension (Category)",
            description="Categorical column to slice and group records by.",
            required=False,
            expected_semantic_types=["CATEGORY", "TEXT"],
            aliases=["status", "type", "category", "group", "class", "state"],
        ),
        EssentialVariable(
            name="primary_record_id",
            display_name="Record Identifier",
            description="Unique identifier to calculate record counts and distinct volumes.",
            required=False,
            expected_semantic_types=["ID", "UUID", "TEXT", "NUMERIC_MEASURE"],
            aliases=["id", "uuid", "code", "key"],
            forbidden_types=[],
        ),
    ],
    kpis=[
        KpiRecipe(
            id="total_records",
            title="Total Records",
            formula_template="COUNT(*)",
            required_variables=[],
            aggregation="COUNT",
            format="number",
            description="Total count of database records.",
        ),
        KpiRecipe(
            id="primary_measure_sum",
            title="Total Value",
            formula_template="SUM({primary_measure})",
            required_variables=["primary_measure"],
            aggregation="SUM",
            format="number",
            description="Total aggregated sum of primary measure.",
        ),
        KpiRecipe(
            id="primary_measure_avg",
            title="Average Value",
            formula_template="AVG({primary_measure})",
            required_variables=["primary_measure"],
            aggregation="AVG",
            format="number",
            description="Average value of primary measure.",
        ),
    ],
    charts=[
        ChartRecipe(
            id="trend_over_time",
            title="Trend Over Time",
            chart_type="line",
            x_axis_var="primary_time_axis",
            y_axis_vars=["primary_measure"],
            description="Timeline trend of the primary metric.",
        ),
        ChartRecipe(
            id="breakdown_by_category",
            title="Breakdown by Category",
            chart_type="bar",
            x_axis_var="primary_dimension",
            y_axis_vars=["primary_measure"],
            description="Distribution across categorical segments.",
        ),
    ],
    default_filters=["primary_dimension"],
)


# ---------------------------------------------------------------------------
# Extensible Registry & Helper Functions
# ---------------------------------------------------------------------------

_DOMAIN_REGISTRY: Dict[str, DomainTemplate] = {
    "ecommerce": ECOMMERCE_TEMPLATE,
    "saas": SAAS_TEMPLATE,
    "healthcare": HEALTHCARE_TEMPLATE,
    "logistics": LOGISTICS_TEMPLATE,
    "finance": FINANCE_TEMPLATE,
    "generic": GENERIC_TEMPLATE,
}


def register_domain_template(template: DomainTemplate) -> None:
    """
    Allows registering new domain templates dynamically at runtime without 
    modifying core architecture.
    """
    _DOMAIN_REGISTRY[template.id.lower()] = template


def get_domain_template(domain_id: Optional[str]) -> DomainTemplate:
    """
    Returns the requested domain template, or defaults safely to GENERIC_TEMPLATE.
    """
    if not domain_id:
        return GENERIC_TEMPLATE
    clean = domain_id.strip().lower()
    return _DOMAIN_REGISTRY.get(clean, GENERIC_TEMPLATE)


def list_domain_templates() -> List[Dict[str, Any]]:
    """
    Returns metadata list of available domain templates for the frontend domain selector.
    """
    return [
        {
            "id": dt.id,
            "name": dt.name,
            "description": dt.description,
            "is_fallback": dt.is_fallback,
            "variable_count": len(dt.essential_variables),
            "kpi_count": len(dt.kpis),
        }
        for dt in _DOMAIN_REGISTRY.values()
    ]
