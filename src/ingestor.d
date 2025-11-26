module ingestor;

import model;
import app;
import std.json;
import std.file;
import std.stdio;
import std.string;
import std.algorithm;
import std.conv;
import std.path;

float mapSeverity(string s)
{
    import std.string : toLower, strip;

    string v = s.toLower().strip();

    if (v == "critical" || v == "crit" || v == "blocker")
        return 10.0;
    if (v == "high" || v == "error" || v == "severe")
        return 7.5;
    if (v == "medium" || v == "moderate" || v == "warning" || v == "major")
        return 5.0;
    if (v == "low" || v == "minor" || v == "info")
        return 2.5;

    if (v.isNumeric)
    {
        try
        {
            return to!float(v);
        }
        catch (Throwable)
        {
        }
    }
    return 5.0;
}

string floatToSeverityLabel(float score)
{
    if (score >= 9.0)
        return "CRITICAL";
    if (score >= 7.0)
        return "HIGH";
    if (score >= 4.0)
        return "MEDIUM";
    return "LOW";
}

bool isFixable(JSONValue result)
{
    JSONValue props = ("properties" in result) ? result["properties"] : parseJSON("{}");

    if ("trivy:fixedVersion" in props)
    {
        string fixedVer = props["trivy:fixedVersion"].str;
        return (fixedVer != "" && fixedVer != "null");
    }
    if ("github:fixAvailable" in props)
    {
        // Handle boolean or string "true"
        auto val = props["github:fixAvailable"];
        if (val.type == JSONType.true_)
            return true;
        if (val.type == JSONType.string)
            return val.str == "true";
        return false;
    }
    // Static analysis fixes
    if ("fix" in result && result["fix"].type != JSONType.null_)
        return true;

    // Default assumption for SAST (Code) is that it is fixable by dev
    return true;
}

float extractSeverity(JSONValue result, JSONValue rules)
{
    // 1. GitHub security-severity
    if ("properties" in result && "security-severity" in result["properties"])
    {
        auto s = result["properties"]["security-severity"];
        if (s.type == JSONType.string)
            return to!float(s.str);
        if (s.type == JSONType.float_)
            return s.floating;
    }

    // 2. Rule lookup
    string ruleId = result["ruleId"].str;
    if (rules.type == JSONType.array)
    {
        foreach (r; rules.array)
        {
            if (r["id"].str == ruleId)
            {
                if ("defaultConfiguration" in r && "level" in r["defaultConfiguration"])
                    return mapSeverity(r["defaultConfiguration"]["level"].str);
                break;
            }
        }
    }

    // 3. Fallback
    if ("level" in result)
        return mapSeverity(result["level"].str);
    return 5.0;
}

import rules.engine; // Import RuleEngine

// ... (existing imports)

void processSarif(string filename, Service[] services, string repoPath, RuleEngine engine, string sarifOutput = "")
{
    if (!filename.exists)
        return;

    writeln("=== Processing SARIF file: ", filename, " ===");
    string content = readText(filename);
    JSONValue json = parseJSON(content);

    if ("runs" !in json)
        return;

    foreach (run; json["runs"].array)
    {
        if ("results" !in run)
            continue;

        JSONValue rules = parseJSON("[]");
        if ("tool" in run && "driver" in run["tool"] && "rules" in run["tool"]["driver"])
        {
            rules = run["tool"]["driver"]["rules"];
        }

        foreach (ref result; run["results"].array)
        {
            string ruleId = ("ruleId" in result) ? result["ruleId"].str : "unknown";

            float sevFloat = extractSeverity(result, rules);
            int baseScore = cast(int)(sevFloat * 10); // 0-100 base
            bool fixable = isFixable(result);
            string severityLabel = floatToSeverityLabel(sevFloat);

            // Path Matching
            string filePath = "";
            if ("locations" in result && result["locations"].array.length > 0)
            {
                auto loc = result["locations"].array[0];
                if ("physicalLocation" in loc && "artifactLocation" in loc["physicalLocation"])
                    filePath = loc["physicalLocation"]["artifactLocation"]["uri"].str;
            }

            // --- ROBUST PATH NORMALIZATION ---
            // 1. Strip file:// prefix if present
            if (filePath.startsWith("file://"))
                filePath = filePath[7 .. $];

            // 2. Dual Resolution Strategy
            // Trivy returns paths relative to the scanned root (e.g. "apps/foo/...")
            // Semgrep returns paths relative to CWD (e.g. "./tests/monorepo-01/apps/foo/...")

            string p1 = filePath.absolutePath.buildNormalizedPath; // Assume relative to CWD
            string p2 = buildPath(repoPath, filePath).absolutePath.buildNormalizedPath; // Assume relative to repoPath

            string findingPath;

            // Prefer the one that actually exists on disk
            if (p1.exists && p1.startsWith(repoPath))
            {
                findingPath = p1;
            }
            else if (p2.exists && p2.startsWith(repoPath))
            {
                findingPath = p2;
            }
            else
            {
                // Fallback 3: Prefix Stripping Strategy
                // If the tool was run from a parent dir (e.g. "project/backend/src/main.py")
                // and we are scanning "backend" (repoPath), we want to match "src/main.py".
                // We iteratively strip the first directory component until we find a match in repoPath.

                import std.array : split;

                auto parts = filePath.split(dirSeparator);
                string bestMatch = "";

                // We try stripping up to N-1 components
                for (size_t i = 1; i < parts.length; i++)
                {
                    string stripped = buildPath(parts[i .. $]);
                    string candidate = buildPath(repoPath, stripped)
                        .absolutePath.buildNormalizedPath;
                    if (candidate.exists && candidate.startsWith(repoPath))
                    {
                        bestMatch = candidate;
                        break; // Found the shortest strip that works (most specific)
                    }
                }

                if (bestMatch != "")
                {
                    findingPath = bestMatch;
                }
                else
                {
                    // Final Fallback: If nothing exists, default to p1 or p2 logic
                    if (p1.startsWith(repoPath))
                        findingPath = p1;
                    else
                        findingPath = p2;
                }
            }

            bool matchedAny = false;

            foreach (service; services)
            {
                string svcDir = service.directory.buildNormalizedPath;
                string svcDocker = service.dockerfilePath.buildNormalizedPath;

                bool isInside = (findingPath == svcDocker) ||
                    (findingPath.startsWith(svcDir));

                if (!isInside)
                    continue;

                matchedAny = true;
                Finding f = new Finding(result);
                f.ruleId = ruleId;
                f.location = filePath;
                f.severity = severityLabel;
                f.baseScore = baseScore; // Set the base score

                // Extract description
                if ("shortDescription" in result && "text" in result["shortDescription"])
                {
                    f.description = result["shortDescription"]["text"].str;
                }
                else if ("message" in result && "text" in result["message"])
                {
                    f.description = result["message"]["text"].str;
                }
                else
                {
                    f.description = "No description available";
                }

                // Clean up description: remove newlines and excessive whitespace
                import std.string : strip, replace;
                import std.array : split, join;

                f.description = f.description.replace("\n", " ").replace("\r", " ");
                f.description = f.description.split().join(" ").strip();

                // --- RULE ENGINE EVALUATION ---
                // Check if finding should be suppressed or modified based on context
                if (service.chart !is null)
                {
                    bool keep = engine.evaluateFinding(f, service.chart);
                    if (!keep)
                        continue; // Suppress finding
                }

                // --- NEW SCORING INTEGRATION ---
                RiskProfile risk = service.chart ? service.chart.risk : new RiskProfile();
                risk.hasFix = fixable; // Update the profile temporarily for calculation

                f.reticulumScore = risk.calculateScore(f.baseScore); // Use f.baseScore which might have been modified
                f.priority = risk.getPriority(f.reticulumScore);

                // Use the rule IDs that were tracked during chart analysis
                f.appliedRules = service.chart ? service.chart.risk.appliedRuleIds : [
                ];

                // Extract line number from location
                int lineNum = 0;
                if ("locations" in result && result["locations"].array.length > 0)
                {
                    auto loc = result["locations"].array[0];
                    if ("physicalLocation" in loc && "region" in loc["physicalLocation"] &&
                        "startLine" in loc["physicalLocation"]["region"])
                    {
                        try
                        {
                            lineNum = loc["physicalLocation"]["region"]["startLine"]
                                .integer.to!int;
                        }
                        catch (Throwable)
                        {
                        }
                    }
                }

                printMatch(service.id, ruleId, filePath, lineNum, baseScore, f.reticulumScore, to!string(
                        f.priority), f.appliedRules, f.description);

                // Enrich SARIF
                JSONValue richData;
                richData["score"] = f.reticulumScore;
                richData["priority"] = to!string(f.priority);
                richData["serviceId"] = service.id;
                richData["exposure"] = (risk.isPublic ? "Public" : "Internal");

                if ("properties" !in result)
                    result.object["properties"] = JSONValue([
                        "reticulum": richData
                    ]);
                else
                    result["properties"].object["reticulum"] = richData;

                service.findings ~= f;
            }
        }
    }

    // Save Output (Optional)
    if (sarifOutput != "")
    {
        try
        {
            std.file.write(sarifOutput, json.toPrettyString());
            writeln("=== Done. Saved enriched SARIF to ", sarifOutput, " ===");
        }
        catch (Throwable e)
        {
            writeln("Error writing SARIF output: ", e.msg);
        }
    }
}
