module rules.engine;

import rules.model;
import model; // For Chart, RiskProfile
import dyaml;
import std.file;
import std.path;
import std.string;
import std.algorithm;
import std.stdio;
import std.conv;
import std.regex;
import std.array;

class RuleEngine
{
    Rule[] rules;

    void loadRules(string directory)
    {
        if (!directory.exists)
            return;

        foreach (string entry; dirEntries(directory, SpanMode.depth))
        {
            if (entry.endsWith(".yaml") || entry.endsWith(".yml"))
            {
                try
                {
                    loadRuleFile(entry);
                }
                catch (Throwable e)
                {
                    writeln("    [RuleEngine] Error loading ", baseName(entry), ": ", e.msg);
                }
            }
        }
        writeln("    [RuleEngine] Loaded ", rules.length, " rules from ", directory);
    }

    private void loadRuleFile(string path)
    {
        try
        {
            Node root = Loader.fromFile(path).load();
            if (root.type != NodeType.mapping)
                return;
            parseRuleNode(root);
        }
        catch (Throwable e)
        {
            writeln("      [Warning] Failed to parse rule in ", baseName(path), ": ", e.msg);
        }
    }

    private void parseRuleNode(Node root)
    {
        Rule rule;

        // Basic Metadata
        if (root.containsKey("id"))
            rule.id = root["id"].as!string;
        if (root.containsKey("name"))
            rule.name = root["name"].as!string;
        if (root.containsKey("description"))
            rule.description = root["description"].as!string;
        if (root.containsKey("severity"))
            rule.severity = root["severity"].as!string;

        // Tags
        if (root.containsKey("tags"))
        {
            foreach (Node t; root["tags"].sequence)
            {
                rule.tags ~= t.as!string;
            }
        }

        // Target
        if (root.containsKey("target"))
        {
            string t = root["target"].as!string.toLower;
            if (t == "values")
                rule.target = RuleTarget.VALUES;
            else if (t == "chart_metadata")
                rule.target = RuleTarget.CHART_METADATA;
            else if (t == "file_content")
                rule.target = RuleTarget.FILE_CONTENT;
            else if (t == "finding")
                rule.target = RuleTarget.FINDING;
        }

        // Match Conditions
        if (root.containsKey("match"))
        {
            foreach (Node m; root["match"].sequence)
            {
                RuleMatch match;
                if (m.containsKey("key"))
                    match.key = m["key"].as!string;

                if (m.containsKey("op"))
                {
                    string op = m["op"].as!string.toLower;
                    if (op == "eq")
                        match.op = MatchOp.EQ;
                    else if (op == "neq")
                        match.op = MatchOp.NEQ;
                    else if (op == "contains")
                        match.op = MatchOp.CONTAINS;
                    else if (op == "regex")
                        match.op = MatchOp.REGEX;
                    else if (op == "exists")
                        match.op = MatchOp.EXISTS;
                    else if (op == "gt")
                        match.op = MatchOp.GT;
                    else if (op == "lt")
                        match.op = MatchOp.LT;
                    else if (op == "contains_tag")
                        match.op = MatchOp.CONTAINS_TAG;
                }
                else
                {
                    match.op = MatchOp.EQ; // Default
                }

                if (m.containsKey("value"))
                {
                    Node val = m["value"];
                    if (val.type == NodeType.boolean)
                        match.boolValue = val.as!bool;
                    else if (val.type == NodeType.integer)
                        match.intValue = val.as!long;
                    else
                        match.value = val.as!string; // Store string representation for others
                }
                rule.match ~= match;
            }
        }

        // Actions
        if (root.containsKey("action"))
        {
            Node act = root["action"];
            if (act.containsKey("risk_profile"))
            {
                Node rp = act["risk_profile"];
                if (rp.containsKey("set_flag"))
                    rule.action.riskProfile.setFlag = rp["set_flag"].as!string;
                if (rp.containsKey("score_multiplier"))
                {
                    // Handle float parsing from string or float/int node
                    try
                    {
                        if (rp["score_multiplier"].type == NodeType.string)
                            rule.action.riskProfile.scoreMultiplier = to!float(
                                rp["score_multiplier"].as!string);
                        else
                            rule.action.riskProfile.scoreMultiplier = rp["score_multiplier"]
                                .as!float;
                    }
                    catch (Throwable)
                    {
                        rule.action.riskProfile.scoreMultiplier = 1.0;
                    }
                }
                else
                {
                    rule.action.riskProfile.scoreMultiplier = 1.0; // Default
                }

                if (rp.containsKey("score_boost"))
                    rule.action.riskProfile.scoreBoost = rp["score_boost"].as!int;
            }
            if (act.containsKey("finding"))
            {
                Node f = act["finding"];
                if (f.containsKey("suppress"))
                    rule.action.finding.suppress = f["suppress"].as!bool;
                if (f.containsKey("score_factor"))
                {
                    try
                    {
                        if (f["score_factor"].type == NodeType.string)
                            rule.action.finding.scoreFactor = to!float(
                                f["score_factor"].as!string);
                        else
                            rule.action.finding.scoreFactor = f["score_factor"].as!float;
                    }
                    catch (Throwable)
                    {
                        rule.action.finding.scoreFactor = 1.0;
                    }
                }
            }
            if (act.containsKey("tags"))
            {
                foreach (Node t; act["tags"].sequence)
                {
                    rule.action.tags ~= t.as!string;
                }
            }
        }

        rules ~= rule;
    }

    // Evaluate rules against Chart Metadata
    void evaluateMetadata(Chart chart)
    {
        foreach (rule; rules)
        {
            if (rule.target != RuleTarget.CHART_METADATA)
                continue;

            bool allMatched = true;
            foreach (m; rule.match)
            {
                if (!checkMetadataMatch(chart, m))
                {
                    allMatched = false;
                    break;
                }
            }

            if (allMatched)
            {
                applyAction(chart, rule);
            }
        }
    }

    // Evaluate rules against Values (YAML Node)
    void evaluateValues(Chart chart, Node values)
    {
        foreach (rule; rules)
        {
            if (rule.target != RuleTarget.VALUES)
                continue;

            bool allMatched = true;
            foreach (m; rule.match)
            {
                if (!checkValuesMatch(values, m))
                {
                    allMatched = false;
                    break;
                }
            }

            if (allMatched)
            {
                applyAction(chart, rule);
            }
        }
    }

    // Evaluate rules against a Finding (Contextual Analysis)
    // Returns true if finding should be KEPT, false if SUPPRESSED
    bool evaluateFinding(Finding finding, Chart chart)
    {
        bool keep = true;

        foreach (rule; rules)
        {
            if (rule.target != RuleTarget.FINDING)
                continue;

            bool allMatched = true;
            foreach (m; rule.match)
            {
                if (!checkFindingMatch(finding, chart, m))
                {
                    allMatched = false;
                    break;
                }
            }

            if (allMatched)
            {
                // Apply Finding Actions
                if (rule.action.finding.suppress)
                {
                    writeln("      → RULE MATCH: ", rule.name, " [SUPPRESSED]");
                    return false; // Immediate suppression
                }

                if (rule.action.finding.scoreFactor != 0.0)
                {
                    writeln("      → RULE MATCH: ", rule.name, " [SCORE REDUCED]");
                    // We modify the finding's base score directly or apply a modifier?
                    // For now, let's modify the base score to reflect the reduced risk.
                    // Note: This is destructive to the finding object.
                    finding.baseScore = cast(int)(
                        finding.baseScore * rule.action.finding.scoreFactor);
                }
            }
        }
        return true;
    }

    private bool checkMetadataMatch(Chart chart, RuleMatch m)
    {
        string valToCheck = "";
        if (m.key == "name")
            valToCheck = chart.name;
        else if (m.key == "path")
            valToCheck = chart.path;
        else
            return false; // Unknown metadata key

        return checkStringMatch(valToCheck, m);
    }

    private bool checkValuesMatch(Node root, RuleMatch m)
    {
        // 1. Navigate to key
        Node current = root;
        string[] parts = m.key.split(".");

        foreach (part; parts)
        {
            if (current.type != NodeType.mapping || !current.containsKey(part))
            {
                // Key not found
                if (m.op == MatchOp.EXISTS)
                    return false; // Exists check fails
                return false;
            }
            current = current[part];
        }

        // 2. Perform Check
        if (m.op == MatchOp.EXISTS)
            return true;

        // Handle types
        if (current.type == NodeType.boolean)
        {
            bool b = current.as!bool;
            if (m.op == MatchOp.EQ)
                return b == m.boolValue;
            if (m.op == MatchOp.NEQ)
                return b != m.boolValue;
            return false;
        }

        if (current.type == NodeType.integer)
        {
            long i = current.as!long;
            if (m.op == MatchOp.EQ)
                return i == m.intValue;
            if (m.op == MatchOp.NEQ)
                return i != m.intValue;
            if (m.op == MatchOp.GT)
                return i > m.intValue;
            if (m.op == MatchOp.LT)
                return i < m.intValue;
            return false;
        }

        if (current.type == NodeType.string)
        {
            return checkStringMatch(current.as!string, m);
        }

        return false;
    }

    private bool checkFindingMatch(Finding f, Chart c, RuleMatch m)
    {
        // 1. Check Finding Properties
        if (m.key == "package_name")
        {
            // Need to extract package name from finding. 
            // This is tricky as it depends on the tool (Trivy vs Semgrep).
            // For Trivy, it's usually in "properties.trivy:packageName" or similar.
            // Let's assume we can access it via f.originalJson or we need to parse it.
            // For now, let's look at the location or message? 
            // Ideally Finding class should have a 'packageName' field.
            // Let's try to find it in the original JSON properties.
            if ("properties" in f.originalJson && "trivy:packageName" in f
                .originalJson["properties"])
            {
                return checkStringMatch(f.originalJson["properties"]["trivy:packageName"].str, m);
            }
            return false;
        }

        if (m.key == "cve_id")
        {
            // ruleId is usually the CVE or check ID
            return checkStringMatch(f.ruleId, m);
        }

        // 2. Check Chart Tags (Context)
        if (m.op == MatchOp.CONTAINS_TAG)
        {
            // Check if the Chart has the tag specified in m.value
            // We need to store tags on the Chart object!
            // Currently Chart doesn't have tags, but we can add them or check RiskProfile tags?
            // Wait, RiskProfile doesn't have tags either, but we added `tags` to RuleAction.
            // We need a place to store "Active Tags" on the Chart.
            // Let's assume Chart has a `string[] tags` field (we need to add it to model.d).
            if (c is null)
                return false;
            return c.tags.canFind(m.value);
        }

        return false;
    }

    private bool checkStringMatch(string actual, RuleMatch m)
    {
        if (m.op == MatchOp.EQ)
            return actual == m.value;
        if (m.op == MatchOp.NEQ)
            return actual != m.value;
        if (m.op == MatchOp.CONTAINS)
            return actual.canFind(m.value);
        if (m.op == MatchOp.REGEX)
        {
            try
            {
                return !matchFirst(actual, regex(m.value)).empty;
            }
            catch (Throwable)
            {
                return false;
            }
        }
        return false;
    }

    private void applyAction(Chart chart, Rule rule)
    {
        writeln("      → RULE MATCH: ", rule.name, " (", rule.id, ")");

        // Track that this rule was applied
        chart.risk.appliedRuleIds ~= rule.id;

        // Apply Risk Profile Modifiers
        auto rp = rule.action.riskProfile;

        if (rp.setFlag.length > 0)
        {
            if (rp.setFlag == "isPublic")
                chart.risk.isPublic = true;
            else if (rp.setFlag == "isPrivileged")
                chart.risk.isPrivileged = true;
            else if (rp.setFlag == "hasDangerousCaps")
                chart.risk.hasDangerousCaps = true;
            else if (rp.setFlag == "hasInternetEgress")
                chart.risk.hasInternetEgress = true;
            else if (rp.setFlag == "mountServiceToken")
                chart.risk.mountServiceToken = true;
        }

        if (rp.scoreMultiplier != 1.0)
        {
            chart.risk.addMultiplier(rp.scoreMultiplier);
        }

        if (rp.scoreBoost != 0)
        {
            chart.risk.addBoost(rp.scoreBoost);
        }

        // Apply Tags
        if (rule.action.tags.length > 0)
        {
            chart.tags ~= rule.action.tags;
            // Deduplicate tags
            chart.tags = chart.tags.sort().uniq().array;
            writeln("      → TAGS APPLIED: ", rule.action.tags);
        }
    }
}
