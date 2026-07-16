//! Path allowlist/denylist for repo discovery walks.
//!
//! Patterns are simple shell globs (`*`, `**`, `?`) matched against the
//! discovered path relative to the walk root, so a decoy directory such as
//! `examples/` or `tests/fixtures/` can be excluded (or the walk restricted
//! to an allowlist) without it silently contributing exposure signal.
//! `--exclude` always wins over `--include`; an empty include list allows
//! everything that isn't excluded (today's behavior, back-compat).

use regex::Regex;
use std::path::Path;

#[derive(Debug, Default)]
pub struct PathFilter {
    include: Vec<Regex>,
    exclude: Vec<Regex>,
}

impl PathFilter {
    pub fn new(include: &[String], exclude: &[String]) -> PathFilter {
        PathFilter {
            include: include.iter().filter_map(|p| glob_to_regex(p)).collect(),
            exclude: exclude.iter().filter_map(|p| glob_to_regex(p)).collect(),
        }
    }

    /// True when `rel_path` (walk-root-relative, `/`-separated) is in scope.
    pub fn is_allowed(&self, rel_path: &str) -> bool {
        let included =
            self.include.is_empty() || self.include.iter().any(|re| re.is_match(rel_path));
        let excluded = self.exclude.iter().any(|re| re.is_match(rel_path));
        included && !excluded
    }
}

/// `path` relative to `root` as a `/`-separated string, for glob matching.
pub fn relative_str(root: &Path, path: &Path) -> String {
    path.strip_prefix(root)
        .unwrap_or(path)
        .to_string_lossy()
        .replace('\\', "/")
}

/// Translate a shell glob into an anchored regex. `*` matches any run
/// excluding `/`, `?` matches one char excluding `/`, and `**` matches zero
/// or more path segments (so `**/x`, `x/**` and `x/**/y` all also match `x`
/// with the double-star segment collapsed to nothing, not just "anything
/// incl. `/`" naively concatenated).
fn glob_to_regex(pattern: &str) -> Option<Regex> {
    let chars: Vec<char> = pattern.chars().collect();
    let n = chars.len();
    let mut re = String::from("^");
    let mut i = 0;
    while i < n {
        // "x/**/y" -> "x(?:/.*)?/y": the double-star segment (with both its
        // surrounding slashes) may collapse to nothing, still leaving one
        // mandatory separating slash before the next literal segment.
        if i + 3 < n
            && chars[i] == '/'
            && chars[i + 1] == '*'
            && chars[i + 2] == '*'
            && chars[i + 3] == '/'
        {
            re.push_str("(?:/.*)?/");
            i += 4;
            continue;
        }
        // Leading "**/x" -> "(?:.*/)?x": may match zero directories.
        if i == 0 && i + 2 < n && chars[i] == '*' && chars[i + 1] == '*' && chars[i + 2] == '/' {
            re.push_str("(?:.*/)?");
            i += 3;
            continue;
        }
        // Trailing "x/**" -> "x(?:/.*)?": may match nothing past `x`.
        if i + 3 == n && chars[i] == '/' && chars[i + 1] == '*' && chars[i + 2] == '*' {
            re.push_str("(?:/.*)?");
            i += 3;
            continue;
        }
        // Bare "**" elsewhere: any run including `/`.
        if chars[i] == '*' && i + 1 < n && chars[i + 1] == '*' {
            re.push_str(".*");
            i += 2;
            continue;
        }
        match chars[i] {
            '*' => re.push_str("[^/]*"),
            '?' => re.push_str("[^/]"),
            c => re.push_str(&regex::escape(&c.to_string())),
        }
        i += 1;
    }
    re.push('$');
    Regex::new(&re).ok()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn single_star_does_not_cross_segments() {
        let f = PathFilter::new(&[], &["examples/*".to_string()]);
        assert!(!f.is_allowed("examples/decoy.yaml"));
        assert!(f.is_allowed("examples/nested/decoy.yaml"));
    }

    #[test]
    fn doublestar_matches_nested_segments() {
        let f = PathFilter::new(&[], &["**/examples/**".to_string()]);
        assert!(!f.is_allowed("examples/decoy.yaml"));
        assert!(!f.is_allowed("apps/svc/examples/nested/decoy.yaml"));
        assert!(f.is_allowed("apps/svc/values.yaml"));
    }

    #[test]
    fn include_allowlist_restricts_to_matches() {
        let f = PathFilter::new(&["charts/payment-api/**".to_string()], &[]);
        assert!(f.is_allowed("charts/payment-api/values.yaml"));
        assert!(!f.is_allowed("charts/other/values.yaml"));
    }

    #[test]
    fn exclude_wins_over_include() {
        let f = PathFilter::new(
            &["charts/**".to_string()],
            &["charts/**/examples/**".to_string()],
        );
        assert!(f.is_allowed("charts/payment-api/values.yaml"));
        assert!(!f.is_allowed("charts/payment-api/examples/decoy.yaml"));
    }

    #[test]
    fn empty_filter_allows_everything() {
        let f = PathFilter::new(&[], &[]);
        assert!(f.is_allowed("anything/at/all.yaml"));
    }
}
