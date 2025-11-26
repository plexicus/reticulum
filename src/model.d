module model;

import std.json;
import std.algorithm; // for min, max
import std.conv; // for to!string

// The Decision Matrix Levels
enum Priority
{
    P0_BLEEDING, // Score 90-100: Public + Critical
    P1_CRITICAL, // Score 70-89:  Public + High OR Internal + Critical
    P2_HIGH, // Score 50-69:  Internal + High
    P3_MEDIUM, // Score 30-49:  Medium issues
    P4_LOW // Score 0-29:   Low/Info
}

class RiskProfile
{
    // --- Context Flags ---
    bool isPublic = false; // Ingress / LoadBalancer
    bool isPrivileged = false; // hostNetwork / privileged: true / runs as root
    bool hasFix = true; // Patch available?
    bool hasDangerousCaps = false; // SYS_ADMIN, NET_ADMIN, etc.
    bool hasInternetEgress = false; // 0.0.0.0/0 allowed
    bool mountServiceToken = true; // automountServiceAccountToken (default true is risky)

    // --- Dynamic Scoring ---
    float[] multipliers;
    int[] boosts;
    string[] appliedRuleIds; // Track which rules were applied

    void addMultiplier(float m)
    {
        multipliers ~= m;
    }

    void addBoost(int b)
    {
        boosts ~= b;
    }

    JSONValue toJson()
    {
        JSONValue j = parseJSON("{}");
        j.object["isPublic"] = JSONValue(isPublic);
        j.object["isPrivileged"] = JSONValue(isPrivileged);
        j.object["hasDangerousCaps"] = JSONValue(hasDangerousCaps);
        j.object["hasInternetEgress"] = JSONValue(hasInternetEgress);
        j.object["mountServiceToken"] = JSONValue(mountServiceToken);
        if (appliedRuleIds.length > 0)
        {
            j.object["appliedRuleIds"] = JSONValue(appliedRuleIds);
        }
        // Calculate a raw score for the report based on a baseline (e.g., 50) just for visibility
        j.object["baseRiskScore"] = JSONValue(calculateScore(50));
        return j;
    }

    // --- robustCalculateScore ---
    // Transforms a raw severity (0-100) into a Contextual Risk Score
    int calculateScore(int baseSeverity)
    {
        float score = cast(float) baseSeverity;

        // 1. Apply Multipliers (Exposure, Context)
        // Default to 1.0 if no multipliers added
        if (multipliers.length == 0)
        {
            // Fallback to legacy logic if no rules ran (or no rules matched)
            // This ensures backward compatibility during migration if rules aren't loaded
            // But ideally we want rules to drive this.
            // For now, let's assume if no multipliers, we treat it as neutral (1.0) 
            // OR we could keep the hardcoded logic here as a fallback?
            // Let's keep it pure: if no rules, no multipliers.
        }
        else
        {
            foreach (m; multipliers)
            {
                score *= m;
            }
        }

        // 2. Apply Boosts (Threats)
        foreach (b; boosts)
        {
            score += b;
        }

        // 3. Actionability Modifier (Hardcoded for now as it's not a rule per se, but could be)
        if (!hasFix)
        {
            score -= 10;
        }

        // Clamping 0-100
        int finalScore = cast(int) score;
        if (finalScore > 100)
            return 100;
        if (finalScore < 0)
            return 0;
        return finalScore;
    }

    Priority getPriority(int score)
    {
        if (score >= 90)
            return Priority.P0_BLEEDING;
        if (score >= 70)
            return Priority.P1_CRITICAL;
        if (score >= 50)
            return Priority.P2_HIGH;
        if (score >= 30)
            return Priority.P3_MEDIUM;
        return Priority.P4_LOW;
    }

    void reset()
    {
        isPublic = false;
        isPrivileged = false;
        hasFix = true;
        hasDangerousCaps = false;
        hasInternetEgress = false;
        mountServiceToken = true;
        multipliers = [];
        boosts = [];
    }
}

class Chart
{
    string name;
    string path;
    RiskProfile risk;
    string[] tags; // Added for Rule Engine tagging

    this(string name, string path)
    {
        this.name = name;
        this.path = path;
        this.risk = new RiskProfile();
    }
}

class Service
{
    string id;
    string name;
    string dockerfilePath;
    string directory;
    Chart chart;
    Finding[] findings;

    this(string id, string name, string path, string dir)
    {
        this.id = id;
        this.name = name;
        this.dockerfilePath = path;
        this.directory = dir;
    }

    JSONValue toJson()
    {
        JSONValue j = parseJSON("{}");
        j.object["id"] = JSONValue(id);
        j.object["type"] = JSONValue(chart !is null ? "HelmVinked" : "Orphan");
        j.object["directory"] = JSONValue(directory);

        if (chart !is null)
        {
            j.object["chartName"] = JSONValue(chart.name);
            j.object["riskProfile"] = chart.risk.toJson();
        }
        else
        {
            j.object["riskProfile"] = JSONValue(null);
        }

        // Findings Summary
        int maxBaseScore = 0;
        int maxReticulumScore = 0;
        JSONValue[] findingsJson;

        foreach (f; findings)
        {
            if (f.baseScore > maxBaseScore)
                maxBaseScore = f.baseScore;
            if (f.reticulumScore > maxReticulumScore)
                maxReticulumScore = f.reticulumScore;

            findingsJson ~= f.toJson();
        }

        j.object["maxBaseScore"] = JSONValue(maxBaseScore);
        j.object["maxReticulumScore"] = JSONValue(maxReticulumScore);
        j.object["findingCount"] = JSONValue(cast(long) findings.length);
        j.object["findings"] = JSONValue(findingsJson);

        return j;
    }
}

class Finding
{
    string ruleId;
    string severity;
    string location;
    int baseScore; // Added: Original severity score (0-100)
    int reticulumScore; // Contextual score
    string description; // Added: Vulnerability description
    Priority priority;
    JSONValue originalJson;
    string[] appliedRules; // Track which rules modified this finding

    this(JSONValue json)
    {
        this.originalJson = json;
    }

    JSONValue toJson()
    {
        JSONValue j = parseJSON("{}");
        j.object["ruleId"] = JSONValue(ruleId);
        j.object["severity"] = JSONValue(severity);
        j.object["location"] = JSONValue(location);
        j.object["baseScore"] = JSONValue(baseScore);
        j.object["reticulumScore"] = JSONValue(reticulumScore);
        j.object["priority"] = JSONValue(to!string(priority));
        if (appliedRules.length > 0)
        {
            j.object["appliedRules"] = JSONValue(appliedRules);
        }
        return j;
    }
}
