module rules.model;

import std.json;

// Target: Where to look?
enum RuleTarget
{
    VALUES, // Check values.yaml content
    CHART_METADATA, // Check Chart.yaml or internal Chart struct (name, path)
    FILE_CONTENT, // Check raw file content (templates, etc.) - Future use
    FINDING // Check vulnerability findings (SARIF)
}

// Operator for matching
enum MatchOp
{
    EQ, // Equals
    NEQ, // Not Equals
    CONTAINS, // String contains / List contains
    REGEX, // Regex match
    EXISTS, // Key exists
    GT, // Greater than (numbers)
    LT, // Less than (numbers)
    CONTAINS_TAG // Check if Chart has a specific tag
}

struct RuleMatch
{
    string key; // Dot notation key (e.g., "ingress.enabled")
    MatchOp op; // Operator
    string value; // String representation of value to match (parsed based on context)
    bool boolValue; // For boolean matches
    long intValue; // For integer matches
}

struct RiskProfileMod
{
    string setFlag; // Name of the flag to set in RiskProfile (e.g., "isPublic")
    float scoreMultiplier; // Multiplier to apply (1.0 = no change)
    int scoreBoost; // Raw points to add
}

struct FindingMod
{
    bool suppress; // Suppress this finding?
    float scoreFactor; // Multiply finding score by this factor (e.g. 0.1)
}

struct RuleAction
{
    RiskProfileMod riskProfile;
    FindingMod finding;
    string[] tags;
}

struct Rule
{
    string id;
    string name;
    string description;
    string severity; // low, medium, high, critical
    string[] tags;

    RuleTarget target;
    RuleMatch[] match; // All must match (AND logic)
    RuleAction action;
}
