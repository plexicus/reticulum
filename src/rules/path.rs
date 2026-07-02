//! Dot-notation path parsing and YAML navigation.
//!
//! Supports:
//! - `a.b.c` — plain nested keys
//! - `a\.b.c` — escaped dots for keys that contain a literal `.`
//!   (e.g. `annotations.eks\.amazonaws\.com/role-arn`)
//! - `containers.*.securityContext` — wildcard over every mapping value or
//!   sequence element at that level
//! - `containers.0.name` — numeric index into sequences

use serde_yaml::Value as Yaml;

/// Split a dot-notation key into segments, honoring `\.` escapes.
pub fn parse_key(key: &str) -> Vec<String> {
    let mut segments = Vec::new();
    let mut current = String::new();
    let mut chars = key.chars().peekable();

    while let Some(c) = chars.next() {
        match c {
            '\\' if chars.peek() == Some(&'.') => {
                chars.next();
                current.push('.');
            }
            '.' => {
                segments.push(std::mem::take(&mut current));
            }
            _ => current.push(c),
        }
    }
    segments.push(current);
    segments
}

/// Walk `root` along `segments`, returning every node the path resolves to.
/// A `*` segment fans out over all mapping values / sequence elements, so the
/// result can hold zero, one or many nodes.
pub fn navigate<'a>(root: &'a Yaml, segments: &[String]) -> Vec<&'a Yaml> {
    let mut current: Vec<&Yaml> = vec![root];

    for segment in segments {
        let mut next: Vec<&Yaml> = Vec::new();
        for node in current {
            if segment == "*" {
                match node {
                    Yaml::Mapping(map) => next.extend(map.values()),
                    Yaml::Sequence(seq) => next.extend(seq.iter()),
                    _ => {}
                }
            } else if let Some(child) = node.get(segment.as_str()) {
                next.push(child);
            } else if let (Yaml::Sequence(seq), Ok(idx)) = (node, segment.parse::<usize>()) {
                if let Some(child) = seq.get(idx) {
                    next.push(child);
                }
            }
        }
        if next.is_empty() {
            return next;
        }
        current = next;
    }
    current
}

#[cfg(test)]
mod tests {
    use super::*;

    fn yaml(s: &str) -> Yaml {
        serde_yaml::from_str(s).unwrap()
    }

    #[test]
    fn plain_segments() {
        assert_eq!(parse_key("a.b.c"), vec!["a", "b", "c"]);
        assert_eq!(parse_key("single"), vec!["single"]);
    }

    #[test]
    fn escaped_dots_stay_in_segment() {
        assert_eq!(
            parse_key("serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"),
            vec![
                "serviceAccount",
                "annotations",
                "eks.amazonaws.com/role-arn"
            ]
        );
    }

    #[test]
    fn navigate_nested_key() {
        let v = yaml("ingress:\n  enabled: true\n");
        let nodes = navigate(&v, &parse_key("ingress.enabled"));
        assert_eq!(nodes, vec![&Yaml::Bool(true)]);
    }

    #[test]
    fn navigate_key_with_literal_dot() {
        let v = yaml("annotations:\n  eks.amazonaws.com/role-arn: arn:aws:iam::123:role/x\n");
        let nodes = navigate(&v, &parse_key("annotations.eks\\.amazonaws\\.com/role-arn"));
        assert_eq!(nodes.len(), 1);
        assert_eq!(nodes[0].as_str(), Some("arn:aws:iam::123:role/x"));
    }

    #[test]
    fn navigate_wildcard_over_sequence() {
        let v = yaml("containers:\n  - securityContext:\n      privileged: false\n  - securityContext:\n      privileged: true\n");
        let nodes = navigate(&v, &parse_key("containers.*.securityContext.privileged"));
        assert_eq!(nodes, vec![&Yaml::Bool(false), &Yaml::Bool(true)]);
    }

    #[test]
    fn navigate_wildcard_over_mapping() {
        let v = yaml("services:\n  web:\n    port: 80\n  db:\n    port: 5432\n");
        let nodes = navigate(&v, &parse_key("services.*.port"));
        assert_eq!(nodes.len(), 2);
    }

    #[test]
    fn navigate_numeric_index() {
        let v = yaml("ports:\n  - 8080\n  - 9090\n");
        let nodes = navigate(&v, &parse_key("ports.1"));
        assert_eq!(nodes.len(), 1);
        assert_eq!(nodes[0].as_i64(), Some(9090));
    }

    #[test]
    fn navigate_missing_path_is_empty() {
        let v = yaml("a: 1\n");
        assert!(navigate(&v, &parse_key("a.b.c")).is_empty());
        assert!(navigate(&v, &parse_key("nope")).is_empty());
    }
}
