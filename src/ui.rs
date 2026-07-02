//! Terminal output: banner, phases and finding presentation.

pub fn print_banner() {
    // Header bar - full width tactical style (Purple background, black text)
    print!("\x1b[48;5;129m\x1b[38;5;232m\x1b[1m CLOUD-NATIVE CONTEXTUAL SECURITY PRIORITIZER BY PLEXICUS ");
    println!("                    \x1b[0m");
    let version_tag = format!(" RETICULUM v{} ", env!("CARGO_PKG_VERSION"));
    print!("\x1b[100m\x1b[30m{}", version_tag);
    println!(
        "{}\x1b[0m\n",
        " ".repeat(80usize.saturating_sub(version_tag.len()))
    );

    // RETICULUM logo in ANSI Shadow font
    const LOGO: [&str; 6] = [
        "██████╗ ███████╗████████╗██╗ ██████╗██╗   ██╗██╗     ██╗   ██╗███╗   ███╗",
        "██╔══██╗██╔════╝╚══██╔══╝██║██╔════╝██║   ██║██║     ██║   ██║████╗ ████║",
        "██████╔╝█████╗     ██║   ██║██║     ██║   ██║██║     ██║   ██║██╔████╔██║",
        "██╔══██╗██╔══╝     ██║   ██║██║     ██║   ██║██║     ██║   ██║██║╚██╔╝██║",
        "██║  ██║███████╗   ██║   ██║╚██████╗╚██████╔╝███████╗╚██████╔╝██║ ╚═╝ ██║",
        "╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝     ╚═╝",
    ];

    // Render logo with purple/violet color (129)
    for line in LOGO {
        println!("\x1b[38;5;129m{}\x1b[0m", line);
    }

    println!();
    println!(
        "   \x1b[38;5;250m[+] MODULE: \x1b[38;5;129mPRIORITIZER\x1b[0m \x1b[38;5;250mONLINE\x1b[0m"
    );
    println!();
}

pub fn print_phase(phase: &str, description: &str) {
    println!(
        "\x1b[94m\n┌─\x1b[0m\x1b[1m {}\x1b[0m\x1b[94m ─────────────────────────────────────────────────────────\x1b[0m",
        phase
    );
    println!("\x1b[94m│ \x1b[0m\x1b[2m{}\x1b[0m", description);
    println!(
        "\x1b[94m└────────────────────────────────────────────────────────────────────\x1b[0m"
    );
}

pub fn print_success(message: &str) {
    println!("\x1b[92m[+] \x1b[0m{}", message);
}

pub fn print_warning(message: &str) {
    println!("\x1b[93m[!] \x1b[0m{}", message);
}

pub fn print_error(message: &str) {
    println!("\x1b[91m[x] \x1b[0m{}", message);
}

pub fn print_info(message: &str) {
    println!("\x1b[96m[*] \x1b[0m{}", message);
}

#[allow(clippy::too_many_arguments)]
pub fn print_match(
    service: &str,
    cve_id: &str,
    file_path: &str,
    line_num: i32,
    base_score: i32,
    final_score: i32,
    priority: &str,
    applied_rules: &[String],
    description: &str,
) {
    // Color code the Reticulum score based on priority
    let score_color = if priority.starts_with("P0") {
        "\x1b[91m" // Bright red for P0_BLEEDING
    } else if priority.starts_with("P1") {
        "\x1b[31m" // Red for P1_CRITICAL
    } else if priority.starts_with("P2") {
        "\x1b[33m" // Yellow for P2_HIGH
    } else if priority.starts_with("P3") {
        "\x1b[34m" // Blue for P3_MEDIUM
    } else {
        "\x1b[2m" // Dim for P4_LOW
    };

    // Format file path with line number
    let full_path = if line_num > 0 {
        format!("{}:{}", file_path, line_num)
    } else {
        file_path.to_string()
    };

    // Format rules
    let rules_str = if applied_rules.is_empty() {
        "none".to_string()
    } else {
        applied_rules.join(", ")
    };

    // Print finding in a clean, simple format
    println!(
        "   \x1b[96m▸\x1b[0m \x1b[1m{}\x1b[0m | \x1b[93m{}\x1b[0m",
        service, cve_id
    );
    println!("     \x1b[2m{}\x1b[0m", full_path);
    println!("     \x1b[2m{}\x1b[0m", description);
    println!(
        "     Tool: \x1b[2m{}\x1b[0m → Reticulum: {}{}\x1b[0m | Rules: \x1b[2m{}\x1b[0m",
        base_score, score_color, final_score, rules_str
    );
    println!();
}

pub fn print_help() {
    println!("\x1b[1mUSAGE:\x1b[0m");
    println!("  reticulum [OPTIONS]\n");
    println!("\x1b[1mOPTIONS:\x1b[0m");
    println!("  \x1b[96m-p, --path\x1b[0m          Path to the source repository \x1b[2m(Required)\x1b[0m");
    println!("  \x1b[96m-s, --sarif\x1b[0m         Path to input SARIF file \x1b[2m(Required unless --scan-only)\x1b[0m");
    println!("  \x1b[96m-o, --output\x1b[0m        Path to save the output JSON report");
    println!(
        "  \x1b[96m    --sarif-output\x1b[0m  Path to save enriched SARIF \x1b[2m(optional)\x1b[0m"
    );
    println!("  \x1b[96m    --scan-only\x1b[0m     Perform exposure analysis only \x1b[2m(ignores SARIF)\x1b[0m");
    println!("  \x1b[96m    --rules\x1b[0m         Base directory containing rule sets \x1b[2m(default: ./rules or next to the binary)\x1b[0m");
    println!("  \x1b[96m    --graph\x1b[0m         Path to save an exposure graph \x1b[2m(Mermaid flowchart)\x1b[0m");
    println!("  \x1b[96m-h, --help\x1b[0m          This help information\n");
    println!("\x1b[1mEXAMPLES:\x1b[0m");
    println!("  \x1b[2m# Full analysis with SARIF input\x1b[0m");
    println!("  \x1b[32m./reticulum -p ./src -s results.sarif\x1b[0m\n");
    println!("  \x1b[2m# Generate enriched SARIF output\x1b[0m");
    println!(
        "  \x1b[32m./reticulum -p ./src -s results.sarif --sarif-output enriched.sarif\x1b[0m\n"
    );
    println!("  \x1b[2m# Exposure analysis only\x1b[0m");
    println!("  \x1b[32m./reticulum -p ./src --scan-only -o exposure.json\x1b[0m\n");
}
