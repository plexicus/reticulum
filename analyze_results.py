import re
import sys

def analyze_file(filename):
    with open(filename, 'r') as f:
        content = f.read()

    # Split by monorepo
    repos = content.split('=== MONOREPO')
    
    print("| Monorepo | Total Findings | Noise Reduced (Lowered) | Escalated (Raised) | Unchanged | Avg Reduction |")
    print("|----------|----------------|-------------------------|--------------------|-----------|---------------|")

    for repo in repos:
        if not repo.strip():
            continue
            
        lines = repo.split('\n')
        repo_id = lines[0].strip().split(' ')[0] if lines[0].strip() else "?"
        
        findings = []
        for line in lines:
            # Match "Tool: 75 → Reticulum: 48"
            # The file might have ANSI codes, so we need to be careful or strip them
            # The previous view_file showed ANSI codes were present in the file but represented as [34m etc.
            # Let's try a regex that ignores potential ANSI codes between numbers
            # Pattern: Tool: <ansi?>(\d+)<ansi?> → Reticulum: <ansi?>(\d+)
            
            # Simple approach: remove all ANSI escape sequences first
            clean_line = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', line)
            
            match = re.search(r'Tool:\s+(\d+)\s+→\s+Reticulum:\s+(\d+)', clean_line)
            if match:
                tool_score = int(match.group(1))
                ret_score = int(match.group(2))
                findings.append((tool_score, ret_score))

        if not findings:
            continue

        total = len(findings)
        lowered = sum(1 for t, r in findings if r < t)
        raised = sum(1 for t, r in findings if r > t)
        unchanged = sum(1 for t, r in findings if r == t)
        
        # Calculate average reduction for lowered items
        reductions = [t - r for t, r in findings if r < t]
        avg_reduction = sum(reductions) / len(reductions) if reductions else 0
        
        print(f"| {repo_id} | {total} | {lowered} ({lowered/total*100:.1f}%) | {raised} ({raised/total*100:.1f}%) | {unchanged} | -{avg_reduction:.1f} pts |")

if __name__ == "__main__":
    analyze_file("analysis_output.txt")
