module mapper;

import model;
import std.file;
import std.path;
import std.stdio;
import std.algorithm;
import std.string;
import std.uni; 
import dyaml;

class Mapper {
    Service[] services;
    Chart[] charts;

    void walk(string rootDir) {
        writeln("=== Discovery Walk: ", rootDir, " ===");
        if (!rootDir.exists) {
            writeln("Error: Root directory does not exist.");
            return;
        }

        foreach (string entryPath; dirEntries(rootDir, SpanMode.breadth)) {
            string fname = baseName(entryPath);
            string fdir = dirName(entryPath);
            string lowerName = fname.toLower();

            // 1. Dockerfile
            if (lowerName.canFind("dockerfile") && !lowerName.endsWith(".dockerignore")) {
                string serviceId = baseName(fdir);
                if (fname.startsWith("Dockerfile.")) serviceId = fname.extension[1..$]; // .worker -> worker
                else if (lowerName != "dockerfile") serviceId = fname.stripExtension; // auth.Dockerfile -> auth

                if (!serviceExists(serviceId)) {
                    services ~= new Service(serviceId, serviceId, entryPath, fdir);
                }
            }

            // 2. Helm Chart (Strict Check)
            if (sicmp(fname, "Chart.yaml") == 0) {
                try {
                    auto node = Loader.fromFile(entryPath).load();
                    string chartName = node["name"].as!string;
                    charts ~= new Chart(chartName, fdir);
                } catch (Exception e) {
                    charts ~= new Chart(baseName(fdir), fdir);
                }
            }
        }
    }

    void link() {
        writeln("=== Linking Services to Charts ===");
        foreach (service; services) {
            Chart bestMatch = null;
            int bestScore = 0;

            foreach (chart; charts) {
                int score = calculateMatchScore(service, chart);
                if (score > bestScore) {
                    bestScore = score;
                    bestMatch = chart;
                }
            }

            if (bestMatch !is null && bestScore > 0) {
                service.chart = bestMatch;
                writeln("  LINKED: ", service.id, " <--> ", bestMatch.name, " (Score: ", bestScore, ")");
            }
        }
    }

    private bool serviceExists(string id) {
        foreach(s; services) if (s.id == id) return true;
        return false;
    }

    private int calculateMatchScore(Service s, Chart c) {
        int score = 0;
        if (sicmp(s.id, c.name) == 0) score += 100;
        if (c.path.startsWith(s.directory) || s.directory.startsWith(c.path)) score += 80;
        
        // Values.yaml image repo check
        string valuesPath = buildPath(c.path, "values.yaml");
        if (valuesPath.exists) {
            try {
                // Simple string scan is faster and safer than full parse for just one check
                string content = readText(valuesPath);
                if (content.canFind(s.id)) score += 60; 
            } catch (Throwable) {}
        }
        return score;
    }
}