//! Rule engine: YAML-defined prioritization rules.

pub mod engine;

pub use engine::RuleEngine;

/// Target: Where to look?
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum RuleTarget {
    #[default]
    Values, // Check values.yaml content
    ChartMetadata, // Check Chart.yaml or internal Chart struct (name, path)
    FileContent,   // Check raw file content (templates, etc.) - Future use
    Finding,       // Check vulnerability findings (SARIF)
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
    Gt,          // Greater than (numbers)
    Lt,          // Less than (numbers)
    ContainsTag, // Check if Chart has a specific tag
}

/// Typed match value.
///
/// AUDIT FIX: the D version kept three parallel fields (`value`, `boolValue`,
/// `intValue`) where the unused ones held indeterminate defaults; a rule whose
/// YAML value type didn't match the checked node type silently compared
/// against those defaults. A tagged enum makes the mismatch explicit.
#[derive(Debug, Clone, Default, PartialEq)]
pub enum MatchValue {
    #[default]
    None,
    Bool(bool),
    Int(i64),
    Str(String),
}

#[derive(Debug, Clone, Default)]
pub struct RuleMatch {
    pub key: String, // Dot notation key (e.g., "ingress.enabled")
    pub op: MatchOp,
    pub value: MatchValue,
}

/// AUDIT FIX: in D these were `float`/`int` struct fields whose default is
/// `float.nan`; a rule without `score_multiplier` produced NaN scores
/// (`NaN != 1.0` is true, so NaN was pushed as a multiplier). `Option`
/// removes that failure mode: absent means "no effect".
#[derive(Debug, Clone, Default)]
pub struct RiskProfileMod {
    pub set_flag: Option<String>,      // Flag to set in RiskProfile (e.g., "isPublic")
    pub score_multiplier: Option<f32>, // Multiplier to apply
    pub score_boost: Option<i32>,      // Raw points to add
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
    pub matches: Vec<RuleMatch>, // All must match (AND logic)
    pub action: RuleAction,
}
