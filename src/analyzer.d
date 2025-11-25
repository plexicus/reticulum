module analyzer;

import model;
import rules.engine; // Import RuleEngine
import std.file;
import std.path;
import std.stdio;
import std.string;
import std.algorithm;
import std.array;
import dyaml.loader;
import dyaml.node;

// ========================
// MAIN LOGIC
// ========================

void analyzeExposure(Chart chart, RuleEngine engine)
{
    if (chart is null)
        return;

    writeln("  [Analyzer] Analyzing chart: ", chart.name, " → ", chart.path);
    chart.risk.reset();

    // 1. Evaluate Metadata Rules
    engine.evaluateMetadata(chart);

    string[] valueFiles;
    try
    {
        foreach (string entry; dirEntries(chart.path, SpanMode.shallow))
        {
            string fname = baseName(entry).toLower;

            // --- FIX: Strictly exclude non-value files ---
            if (fname == "chart.yaml" || fname == "chart.yml" || fname == "chart.lock" || fname.startsWith(
                    ".helm"))
            {
                continue;
            }

            // Allow standard values.yaml, variations like values-prod.yaml, or specific environment files
            bool isYaml = (fname.endsWith(".yaml") || fname.endsWith(".yml"));
            bool looksLikeValues = (fname.startsWith("values") || fname == "prod.yaml" || fname == "staging.yaml" || fname == "dev.yaml");

            if (isYaml && looksLikeValues)
            {
                valueFiles ~= entry;
            }
        }
    }
    catch (Throwable)
    {
    }

    valueFiles.sort();

    foreach (path; valueFiles)
    {
        if (path.exists)
        {
            writeln("    → Loading values: ", baseName(path));
            analyzeValuesFile(chart, path, engine);
        }
    }

    // analyzeTemplates(chart); // Deprecated for now, or needs to be ported to RuleEngine (FILE_CONTENT target)
    // For now, we rely on values.yaml analysis as per the plan. Template analysis is complex to do with simple rules.
    // If we need template analysis, we should add a FILE_CONTENT target to RuleEngine later.

    writeln("    [Final Risk Profile]");
    writeln("      • Public Exposure    : ", chart.risk.isPublic ? "YES" : "NO");
    writeln("      • Privileged         : ", chart.risk.isPrivileged ? "YES" : "NO");
    writeln("      • Dangerous Caps     : ", chart.risk.hasDangerousCaps ? "YES" : "NO");
    writeln("      • Svc Token Mount    : ", chart.risk.mountServiceToken ? "YES (Default)"
            : "NO (Secured)");
}

private void analyzeValuesFile(Chart chart, string path, RuleEngine engine)
{
    try
    {
        Node root = Loader.fromFile(path).load();

        if (root.type != NodeType.mapping)
            return;

        // 2. Evaluate Values Rules
        engine.evaluateValues(chart, root);

    }
    catch (Throwable e)
    {
        writeln("    [Error] Failed to parse ", baseName(path), ": ", e.msg);
    }
}
