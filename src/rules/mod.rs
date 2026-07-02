//! Rule engine: YAML-defined prioritization rules.
//!
//! v2 DSL summary (fully backward compatible with v1 rules):
//! - `match:`  list — ALL conditions must hold (AND)
//! - `any:`    list — at least ONE condition must hold (OR), combined with `match:`
//! - key paths support `\.` escapes, `*` wildcards and numeric indices
//! - ops: eq, neq, contains, regex, exists, not_exists, gt, lt, gte, lte, in, contains_tag
//! - actions: risk_profile.set_flag (legacy, sets true), risk_profile.set_flags
//!   (map of flag -> bool), score_multiplier, score_boost, finding.suppress,
//!   finding.score_factor, tags
//! - targets: values, chart_metadata, finding, manifest (with optional `kind:`)

pub mod engine;
pub mod parser;
pub mod path;

pub use engine::RuleEngine;

/// Target: Where to look?
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum RuleTarget {
    #[default]
    Values, // Check values.yaml content
    ChartMetadata, // Check Chart.yaml or internal Chart struct (name, path)
    FileContent,   // Check raw file content (templates, etc.) - Future use
    Finding,       // Check vulnerability findings (SARIF)
    Manifest,      // Check raw Kubernetes manifest documents (filtered by `kind:`)
}

/// Operator for matching
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum MatchOp {
    #[default]
    Eq, // Equals
    Neq,         // Not Equals
    Contains,    // String contains / List contains
    Regex,       // Regex match
    Exists,      // Key exists
    NotExists,   // Key does not exist
    Gt,          // Greater than (numbers)
    Lt,          // Less than (numbers)
    Gte,         // Greater than or equal (numbers)
    Lte,         // Less than or equal (numbers)
    In,          // Value is one of a list of options
    ContainsTag, // Check if Chart has a specific tag
}

/// Typed match value. A tagged enum keeps type mismatches explicit instead of
/// silently comparing against indeterminate defaults (a bug in the D original).
#[derive(Debug, Clone, Default, PartialEq)]
pub enum MatchValue {
    #[default]
    None,
    Bool(bool),
    Int(i64),
    Float(f64),
    Str(String),
    List(Vec<String>),
}

#[derive(Debug, Clone, Default)]
pub struct RuleMatch {
    pub key: String, // Dot notation key (e.g., "ingress.enabled")
    pub op: MatchOp,
    pub value: MatchValue,
}

/// `Option` (not bare floats) so that "field absent" can never contaminate the
/// score — the D original's NaN defaults did exactly that.
#[derive(Debug, Clone, Default)]
pub struct RiskProfileMod {
    pub set_flag: Option<String>,       // Legacy: flag to set to true
    pub set_flags: Vec<(String, bool)>, // v2: explicit flag -> value pairs
    pub score_multiplier: Option<f32>,  // Multiplier to apply
    pub score_boost: Option<i32>,       // Raw points to add
}

#[derive(Debug, Clone, Default)]
pub struct FindingMod {
    pub suppress: bool,            // Suppress this finding?
    pub score_factor: Option<f32>, // Multiply finding score by this factor (e.g. 0.1)
}

#[derive(Debug, Clone, Default)]
pub struct RuleAction {
    pub risk_profile: RiskProfileMod,
    pub finding: FindingMod,
    pub tags: Vec<String>,
}

#[derive(Debug, Clone, Default)]
pub struct Rule {
    pub id: String,
    pub name: String,
    pub description: String,
    pub severity: String, // low, medium, high, critical
    pub tags: Vec<String>,

    pub target: RuleTarget,
    /// For `manifest` rules: only evaluate documents of this Kubernetes kind
    /// (case-insensitive). None = every document.
    pub kind: Option<String>,
    pub matches: Vec<RuleMatch>,     // All must match (AND logic)
    pub any_matches: Vec<RuleMatch>, // At least one must match (OR logic)
    pub action: RuleAction,
}

impl Rule {
    /// Combined match semantics: every `match:` condition holds AND, if an
    /// `any:` block is present, at least one of its conditions holds.
    pub fn matches_with(&self, check: impl Fn(&RuleMatch) -> bool) -> bool {
        self.matches.iter().all(&check)
            && (self.any_matches.is_empty() || self.any_matches.iter().any(&check))
    }
}
