/**
 * Reticulum - Contextual Security Prioritizer for Kubernetes
 * 
 * Author: Jose Ramon Palanco <jose.palanco@plexicus.ai>
 * By: PLEXICUS (https://www.plexicus.ai)
 * License: MIT
 */

module app;

import std.stdio;
import std.getopt;
import std.json;
import mapper;
import analyzer;
import ingestor;
import rules.engine;
import std.file;
import std.path;
import std.algorithm;
import std.string;
import std.conv;

// ANSI Color Codes - Red Alert Palette
enum Color : string
{
    RESET = "\033[0m",
    BOLD = "\033[1m",
    DIM = "\033[2m",
    RED = "\033[31m",
    GREEN = "\033[32m",
    YELLOW = "\033[33m",
    BLUE = "\033[34m",
    MAGENTA = "\033[35m",
    CYAN = "\033[36m",
    WHITE = "\033[37m",
    BRIGHT_RED = "\033[91m",
    BRIGHT_GREEN = "\033[92m",
    BRIGHT_YELLOW = "\033[93m",
    BRIGHT_BLUE = "\033[94m",
    BRIGHT_MAGENTA = "\033[95m",
    BRIGHT_CYAN = "\033[96m",
    // Extended colors for brutal theme
    COL_RED = "\033[38;5;196m", // Laser red
    COL_GRY = "\033[38;5;244m", // Metallic gray
    BG_RED = "\033[48;5;196m\033[38;5;232m" // Red background, black text
}

void printBanner()
{
    // Header bar - full width tactical style (Purple background, black text)
    write(
        "\033[48;5;129m\033[38;5;232m\033[1m CLOUD-NATIVE CONTEXTUAL SECURITY PRIORITIZER BY PLEXICUS ");
    write("                    \033[0m\n");
    write("\033[100m\033[30m RETICULUM v1.0 ");
    write("                                                                \033[0m\n\n");

    // RETICULUM logo in ANSI Shadow font
    const string[] logo = [
        "██████╗ ███████╗████████╗██╗ ██████╗██╗   ██╗██╗     ██╗   ██╗███╗   ███╗",
        "██╔══██╗██╔════╝╚══██╔══╝██║██╔════╝██║   ██║██║     ██║   ██║████╗ ████║",
        "██████╔╝█████╗     ██║   ██║██║     ██║   ██║██║     ██║   ██║██╔████╔██║",
        "██╔══██╗██╔══╝     ██║   ██║██║     ██║   ██║██║     ██║   ██║██║╚██╔╝██║",
        "██║  ██║███████╗   ██║   ██║╚██████╗╚██████╔╝███████╗╚██████╔╝██║ ╚═╝ ██║",
        "╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝     ╚═╝"
    ];

    // Render logo with purple/violet color (129)
    foreach (line; logo)
    {
        write("\033[38;5;129m", line, "\033[0m\n");
    }

    writeln();
    write(
        "   \033[38;5;250m[+] MODULE: \033[38;5;129mPRIORITIZER\033[0m \033[38;5;250mONLINE\033[0m\n");
    writeln();
}

void printPhase(string phase, string description)
{
    write("\033[94m\n┌─\033[0m\033[1m " ~ phase ~ "\033[0m\033[94m ─────────────────────────────────────────────────────────\033[0m\n");
    write("\033[94m│ \033[0m\033[2m" ~ description ~ "\033[0m\n");
    write("\033[94m└────────────────────────────────────────────────────────────────────\033[0m\n");
}

void printSuccess(string message)
{
    writeln("\033[92m[+] \033[0m" ~ message);
}

void printWarning(string message)
{
    writeln("\033[93m[!] \033[0m" ~ message);
}

void printError(string message)
{
    writeln("\033[91m[x] \033[0m" ~ message);
}

void printInfo(string message)
{
    writeln("\033[96m[*] \033[0m" ~ message);
}

// Track if this is the first finding for header
bool firstFinding = true;

void printMatch(string service, string cveId, string filePath, int lineNum, int baseScore, int finalScore, string priority, string[] appliedRules, string description)
{
    if (firstFinding)
    {
        writeln("");
        firstFinding = false;
    }

    // Color code the Reticulum score based on priority
    string scoreColor;
    if (priority.startsWith("P0"))
        scoreColor = "\033[91m"; // Bright red for P0_BLEEDING
    else if (priority.startsWith("P1"))
        scoreColor = "\033[31m"; // Red for P1_CRITICAL
    else if (priority.startsWith("P2"))
        scoreColor = "\033[33m"; // Yellow for P2_HIGH
    else if (priority.startsWith("P3"))
        scoreColor = "\033[34m"; // Blue for P3_MEDIUM
    else
        scoreColor = "\033[2m"; // Dim for P4_LOW

    import std.string : leftJustify;
    import std.array : join;

    // Format file path with line number
    string lineStr = lineNum > 0 ? ":" ~ to!string(lineNum) : "";
    string fullPath = filePath ~ lineStr;

    // Format rules
    string rulesStr = appliedRules.length > 0 ? appliedRules.join(", ") : "none";

    // Print finding in a clean, simple format
    writeln("   \033[96m▸\033[0m \033[1m" ~ service ~ "\033[0m | \033[93m" ~ cveId ~ "\033[0m");
    writeln("     \033[2m" ~ fullPath ~ "\033[0m");
    writeln("     \033[2m" ~ description ~ "\033[0m");
    writeln("     Tool: \033[2m" ~ to!string(baseScore) ~ "\033[0m → Reticulum: " ~ scoreColor ~ to!string(
            finalScore) ~ "\033[0m | Rules: \033[2m" ~ rulesStr ~ "\033[0m");
    writeln("");
}

void printHelp()
{
    writeln("\033[1mUSAGE:\033[0m");
    writeln("  reticulum [OPTIONS]\n");
    writeln("\033[1mOPTIONS:\033[0m");
    writeln(
        "  \033[96m-p, --path\033[0m          Path to the source repository \033[2m(Required)\033[0m");
    writeln(
        "  \033[96m-s, --sarif\033[0m         Path to input SARIF file \033[2m(Required unless --scan-only)\033[0m");
    writeln("  \033[96m-o, --output\033[0m        Path to save the output JSON report");
    writeln(
        "  \033[96m    --sarif-output\033[0m  Path to save enriched SARIF \033[2m(optional)\033[0m");
    writeln(
        "  \033[96m    --scan-only\033[0m     Perform exposure analysis only \033[2m(ignores SARIF)\033[0m");
    writeln("  \033[96m-h, --help\033[0m          This help information\n");
    writeln("\033[1mEXAMPLES:\033[0m");
    writeln("  \033[2m# Full analysis with SARIF input\033[0m");
    writeln("  \033[32m./reticulum -p ./src -s results.sarif\033[0m\n");
    writeln("  \033[2m# Generate enriched SARIF output\033[0m");
    writeln(
        "  \033[32m./reticulum -p ./src -s results.sarif --sarif-output enriched.sarif\033[0m\n");
    writeln("  \033[2m# Exposure analysis only\033[0m");
    writeln("  \033[32m./reticulum -p ./src --scan-only -o exposure.json\033[0m\n");
}

void main(string[] args)
{
    string repoPath;
    string sarifInput;
    string jsonOutput;
    string sarifOutput;
    bool scanOnly = false;

    printBanner();

    try
    {
        auto helpInfo = getopt(
            args,
            "path|p", "Path to the source repository (Required)", &repoPath,
            "sarif|s", "Path to input SARIF file (Required unless --scan-only)", &sarifInput,
            "output|o", "Path to save the output JSON report", &jsonOutput,
            "sarif-output", "Path to save enriched SARIF (optional)", &sarifOutput,
            "scan-only", "Perform exposure analysis only (ignores SARIF)", &scanOnly
        );

        if (helpInfo.helpWanted || repoPath == "")
        {
            printHelp();
            return;
        }
    }
    catch (Exception e)
    {
        printError("Error parsing arguments: " ~ e.msg);
        return;
    }

    if (!scanOnly && sarifInput == "")
    {
        printError("--sarif is required unless --scan-only is used.");
        return;
    }

    // 1. Resolve absolute path for the repo
    string absRepoPath = repoPath.absolutePath.buildNormalizedPath;
    printInfo("Target Repository: " ~ absRepoPath);

    // --- Initialize Rule Engine ---
    printInfo("Initializing Rule Engine...");
    RuleEngine engine = new RuleEngine();

    // Load rules from organized directories
    if (exists("rules/exposure"))
        engine.loadRules("rules/exposure");
    if (exists("rules/security"))
        engine.loadRules("rules/security");
    if (exists("rules/scoring"))
        engine.loadRules("rules/scoring");

    // Load custom rules last (can override defaults)
    if (exists("rules/custom"))
    {
        engine.loadRules("rules/custom");
    }

    printPhase("Phase 1: Service Discovery", "Mapping services and Helm charts");
    Mapper m = new Mapper();
    m.walk(absRepoPath); // Changed to use absRepoPath
    m.link();

    printPhase("Phase 2: Exposure Analysis", "Analyzing Kubernetes deployment configurations");
    foreach (s; m.services)
    {
        if (s.chart)
            analyzer.analyzeExposure(s.chart, engine);
    }

    if (scanOnly)
    {
        printWarning("Mode: Exposure Analysis Only (Skipping SARIF ingestion)");

        // 1. Build the Rich JSON
        JSONValue[] serviceList;
        foreach (s; m.services)
        {
            serviceList ~= s.toJson();
        }

        JSONValue root = parseJSON("{}");
        root.object["services"] = JSONValue(serviceList);
        root.object["totalServices"] = JSONValue(cast(long) m.services.length);
        root.object["scanType"] = JSONValue("exposure-audit");

        // 2. Output Handling
        if (jsonOutput != "")
        {
            try
            {
                std.file.write(jsonOutput, root.toPrettyString());
                printSuccess("Exposure report saved to: " ~ jsonOutput);
            }
            catch (Exception e)
            {
                printError("Error writing output: " ~ e.msg);
            }
        }
        else
        {
            // Fallback: If no file specified, print to stdout
            writeln(root.toPrettyString());
        }

        return; // EXIT PROGRAM HERE
    }

    printPhase("Phase 3: Vulnerability Scoring", "Ingesting SARIF and applying contextual scoring");
    processSarif(sarifInput, m.services, absRepoPath, engine, sarifOutput);

    // --- Generate JSON Report (Full Scan) ---
    if (jsonOutput != "")
    {
        JSONValue[] serviceList;
        foreach (s; m.services)
        {
            serviceList ~= s.toJson();
        }

        JSONValue root = parseJSON("{}");
        root.object["services"] = JSONValue(serviceList);
        root.object["totalServices"] = JSONValue(cast(long) m.services.length);
        root.object["scanType"] = JSONValue("full-analysis");

        try
        {
            std.file.write(jsonOutput, root.toPrettyString());
            printSuccess("Full analysis report saved to: " ~ jsonOutput);
        }
        catch (Exception e)
        {
            printError("Error writing JSON output: " ~ e.msg);
        }
    }

    printSuccess("Reticulum Analysis Complete.");
}
