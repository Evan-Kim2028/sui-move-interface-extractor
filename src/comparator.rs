use serde_json::Value;
use std::collections::HashSet;

use crate::bytecode::get_object;
use crate::normalization::{
    abilities_from_value, bytecode_type_to_canonical_json, rpc_type_to_canonical_json,
    rpc_visibility_to_string,
};
use crate::types::{
    BytecodeModuleCheck, InterfaceCompareMismatch, InterfaceCompareSummary, ModuleSetDiff,
};
use crate::utils::canonicalize_json_value;

pub struct InterfaceCompareOptions {
    pub max_mismatches: usize,
    pub include_values: bool,
}

pub fn compare_interface_rpc_vs_bytecode(
    _package_id: &str,
    rpc_interface_value: &Value,
    bytecode_interface_value: &Value,
    opts: InterfaceCompareOptions,
) -> (InterfaceCompareSummary, Vec<InterfaceCompareMismatch>) {
    let mut mismatches: Vec<InterfaceCompareMismatch> = Vec::new();
    let mut mismatch_count_total: usize = 0;

    let mut push_mismatch =
        |path: String, reason: String, rpc: Option<Value>, bytecode: Option<Value>| {
            mismatch_count_total += 1;
            if mismatches.len() < opts.max_mismatches {
                let (rpc, bytecode) = if opts.include_values {
                    (rpc, bytecode)
                } else {
                    (None, None)
                };
                mismatches.push(InterfaceCompareMismatch {
                    path,
                    reason,
                    rpc,
                    bytecode,
                });
            }
        };

    let empty_modules = serde_json::Map::new();
    let rpc_modules = rpc_interface_value
        .get("modules")
        .and_then(Value::as_object)
        .unwrap_or(&empty_modules);
    let byte_modules = bytecode_interface_value
        .get("modules")
        .and_then(Value::as_object)
        .unwrap_or(&empty_modules);

    let mut rpc_module_names: Vec<&String> = rpc_modules.keys().collect();
    rpc_module_names.sort();
    let mut byte_module_names: Vec<&String> = byte_modules.keys().collect();
    byte_module_names.sort();

    let rpc_set: HashSet<&str> = rpc_module_names.iter().map(|s| s.as_str()).collect();
    let byte_set: HashSet<&str> = byte_module_names.iter().map(|s| s.as_str()).collect();

    let modules_missing_in_bytecode: Vec<&str> = rpc_module_names
        .iter()
        .map(|s| s.as_str())
        .filter(|m| !byte_set.contains(m))
        .collect();
    for m in &modules_missing_in_bytecode {
        push_mismatch(
            format!("modules/{m}"),
            "module missing in bytecode".to_string(),
            rpc_modules.get(*m).cloned(),
            None,
        );
    }

    let modules_extra_in_bytecode: Vec<&str> = byte_module_names
        .iter()
        .map(|s| s.as_str())
        .filter(|m| !rpc_set.contains(m))
        .collect();
    for m in &modules_extra_in_bytecode {
        push_mismatch(
            format!("modules/{m}"),
            "extra module in bytecode".to_string(),
            None,
            byte_modules.get(*m).cloned(),
        );
    }

    let mut modules_compared = 0usize;
    let mut structs_compared = 0usize;
    let mut struct_mismatches = 0usize;
    let mut functions_compared = 0usize;
    let mut function_mismatches = 0usize;

    let mut intersection: Vec<&str> = rpc_module_names
        .iter()
        .map(|s| s.as_str())
        .filter(|m| byte_set.contains(*m))
        .collect();
    intersection.sort();

    for module_name in intersection {
        modules_compared += 1;

        let rpc_mod = rpc_modules.get(module_name).unwrap_or(&Value::Null);
        let byte_mod = byte_modules.get(module_name).unwrap_or(&Value::Null);

        let rpc_structs = get_object(rpc_mod, &["structs"])
            .cloned()
            .unwrap_or_default();
        let byte_structs = get_object(byte_mod, &["structs"])
            .cloned()
            .unwrap_or_default();

        let mut rpc_struct_names: Vec<String> = rpc_structs.keys().cloned().collect();
        rpc_struct_names.sort();
        let mut byte_struct_names: Vec<String> = byte_structs.keys().cloned().collect();
        byte_struct_names.sort();

        let byte_struct_set: HashSet<&str> = byte_struct_names.iter().map(|s| s.as_str()).collect();
        for sname in &rpc_struct_names {
            if !byte_struct_set.contains(sname.as_str()) {
                struct_mismatches += 1;
                push_mismatch(
                    format!("modules/{module_name}/structs/{sname}"),
                    "struct missing in bytecode".to_string(),
                    rpc_structs.get(sname).cloned(),
                    None,
                );
            }
        }

        for sname in &rpc_struct_names {
            let Some(rpc_struct) = rpc_structs.get(sname) else {
                continue;
            };
            let Some(byte_struct) = byte_structs.get(sname) else {
                continue;
            };
            structs_compared += 1;

            let rpc_abilities = rpc_struct
                .get("abilities")
                .map(abilities_from_value)
                .unwrap_or_default();
            let byte_abilities = byte_struct
                .get("abilities")
                .map(abilities_from_value)
                .unwrap_or_default();
            if rpc_abilities != byte_abilities {
                struct_mismatches += 1;
                push_mismatch(
                    format!("modules/{module_name}/structs/{sname}/abilities"),
                    "abilities mismatch".to_string(),
                    rpc_struct.get("abilities").cloned(),
                    byte_struct.get("abilities").cloned(),
                );
            }

            let rpc_tps = rpc_struct
                .get("typeParameters")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default();
            let byte_tps = byte_struct
                .get("type_params")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default();
            if rpc_tps.len() != byte_tps.len() {
                struct_mismatches += 1;
                push_mismatch(
                    format!("modules/{module_name}/structs/{sname}/type_params"),
                    format!(
                        "type param arity mismatch (rpc={} bytecode={})",
                        rpc_tps.len(),
                        byte_tps.len()
                    ),
                    rpc_struct.get("typeParameters").cloned(),
                    byte_struct.get("type_params").cloned(),
                );
            } else {
                for (i, (rtp, btp)) in rpc_tps.iter().zip(byte_tps.iter()).enumerate() {
                    let rpc_constraints = rtp
                        .get("constraints")
                        .map(abilities_from_value)
                        .unwrap_or_default();
                    let rpc_is_phantom = rtp
                        .get("isPhantom")
                        .and_then(Value::as_bool)
                        .unwrap_or(false);
                    let byte_constraints = btp
                        .get("constraints")
                        .map(abilities_from_value)
                        .unwrap_or_default();
                    let byte_is_phantom = btp
                        .get("is_phantom")
                        .and_then(Value::as_bool)
                        .unwrap_or(false);
                    if rpc_constraints != byte_constraints || rpc_is_phantom != byte_is_phantom {
                        struct_mismatches += 1;
                        push_mismatch(
                            format!("modules/{module_name}/structs/{sname}/type_params[{i}]"),
                            "struct type param mismatch".to_string(),
                            Some(
                                serde_json::json!({"constraints": rpc_constraints, "is_phantom": rpc_is_phantom}),
                            ),
                            Some(
                                serde_json::json!({"constraints": byte_constraints, "is_phantom": byte_is_phantom}),
                            ),
                        );
                    }
                }
            }

            let rpc_fields = rpc_struct
                .get("fields")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default();
            let byte_fields = byte_struct
                .get("fields")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default();
            let byte_is_native = byte_struct
                .get("is_native")
                .and_then(Value::as_bool)
                .unwrap_or(false);
            if byte_is_native && rpc_fields.is_empty() {
            } else if rpc_fields.len() != byte_fields.len() {
                struct_mismatches += 1;
                push_mismatch(
                    format!("modules/{module_name}/structs/{sname}/fields"),
                    format!(
                        "field count mismatch (rpc={} bytecode={})",
                        rpc_fields.len(),
                        byte_fields.len()
                    ),
                    rpc_struct.get("fields").cloned(),
                    byte_struct.get("fields").cloned(),
                );
            } else {
                for (i, (rf, bf)) in rpc_fields.iter().zip(byte_fields.iter()).enumerate() {
                    let rname = rf.get("name").and_then(Value::as_str).unwrap_or("");
                    let bname = bf.get("name").and_then(Value::as_str).unwrap_or("");
                    if rname != bname {
                        struct_mismatches += 1;
                        push_mismatch(
                            format!("modules/{module_name}/structs/{sname}/fields[{i}]/name"),
                            "field name mismatch".to_string(),
                            rf.get("name").cloned(),
                            bf.get("name").cloned(),
                        );
                        continue;
                    }
                    let rty = rf.get("type").unwrap_or(&Value::Null);
                    let bty = bf.get("type").unwrap_or(&Value::Null);
                    let rcanon = rpc_type_to_canonical_json(rty);
                    let bcanon = bytecode_type_to_canonical_json(bty);
                    match (rcanon, bcanon) {
                        (Ok(mut r), Ok(mut b)) => {
                            canonicalize_json_value(&mut r);
                            canonicalize_json_value(&mut b);
                            if r != b {
                                struct_mismatches += 1;
                                push_mismatch(
                                    format!(
                                        "modules/{module_name}/structs/{sname}/fields[{i}]/type"
                                    ),
                                    "field type mismatch".to_string(),
                                    Some(r),
                                    Some(b),
                                );
                            }
                        }
                        (Err(e), _) => {
                            struct_mismatches += 1;
                            push_mismatch(
                                format!("modules/{module_name}/structs/{sname}/fields[{i}]/type"),
                                format!("rpc type parse error: {:#}", e),
                                Some(rty.clone()),
                                None,
                            );
                        }
                        (_, Err(e)) => {
                            struct_mismatches += 1;
                            push_mismatch(
                                format!("modules/{module_name}/structs/{sname}/fields[{i}]/type"),
                                format!("bytecode type parse error: {:#}", e),
                                None,
                                Some(bty.clone()),
                            );
                        }
                    }
                }
            }
        }

        let rpc_funcs = get_object(rpc_mod, &["exposedFunctions", "exposed_functions"])
            .cloned()
            .unwrap_or_default();
        let byte_funcs = get_object(byte_mod, &["functions"])
            .cloned()
            .unwrap_or_default();

        let mut rpc_func_names: Vec<String> = rpc_funcs.keys().cloned().collect();
        rpc_func_names.sort();

        for fname in &rpc_func_names {
            let Some(rpc_fun) = rpc_funcs.get(fname) else {
                continue;
            };
            let Some(byte_fun) = byte_funcs.get(fname) else {
                function_mismatches += 1;
                push_mismatch(
                    format!("modules/{module_name}/functions/{fname}"),
                    "function missing in bytecode".to_string(),
                    Some(rpc_fun.clone()),
                    None,
                );
                continue;
            };
            functions_compared += 1;

            let rpc_vis = rpc_fun
                .get("visibility")
                .and_then(rpc_visibility_to_string)
                .unwrap_or_else(|| "<unknown>".to_string());
            let byte_vis = byte_fun
                .get("visibility")
                .and_then(Value::as_str)
                .unwrap_or("<missing>")
                .to_string();
            if rpc_vis != byte_vis {
                function_mismatches += 1;
                push_mismatch(
                    format!("modules/{module_name}/functions/{fname}/visibility"),
                    "visibility mismatch".to_string(),
                    rpc_fun.get("visibility").cloned(),
                    byte_fun.get("visibility").cloned(),
                );
            }

            let rpc_entry = rpc_fun
                .get("isEntry")
                .and_then(Value::as_bool)
                .unwrap_or(false);
            let byte_entry = byte_fun
                .get("is_entry")
                .and_then(Value::as_bool)
                .unwrap_or(false);
            if rpc_entry != byte_entry {
                function_mismatches += 1;
                push_mismatch(
                    format!("modules/{module_name}/functions/{fname}/is_entry"),
                    "entry mismatch".to_string(),
                    rpc_fun.get("isEntry").cloned(),
                    byte_fun.get("is_entry").cloned(),
                );
            }

            let rpc_tps = rpc_fun
                .get("typeParameters")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default();
            let byte_tps = byte_fun
                .get("type_params")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default();
            if rpc_tps.len() != byte_tps.len() {
                function_mismatches += 1;
                push_mismatch(
                    format!("modules/{module_name}/functions/{fname}/type_params"),
                    format!(
                        "type param arity mismatch (rpc={} bytecode={})",
                        rpc_tps.len(),
                        byte_tps.len()
                    ),
                    rpc_fun.get("typeParameters").cloned(),
                    byte_fun.get("type_params").cloned(),
                );
            } else {
                for (i, (rtp, btp)) in rpc_tps.iter().zip(byte_tps.iter()).enumerate() {
                    let rpc_constraints = abilities_from_value(rtp);
                    let byte_constraints = btp
                        .get("constraints")
                        .map(abilities_from_value)
                        .unwrap_or_default();
                    if rpc_constraints != byte_constraints {
                        function_mismatches += 1;
                        push_mismatch(
                            format!("modules/{module_name}/functions/{fname}/type_params[{i}]"),
                            "function type param constraints mismatch".to_string(),
                            Some(serde_json::json!({"constraints": rpc_constraints})),
                            Some(serde_json::json!({"constraints": byte_constraints})),
                        );
                    }
                }
            }

            let rpc_params = rpc_fun
                .get("parameters")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default();
            let byte_params = byte_fun
                .get("params")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default();
            if rpc_params.len() != byte_params.len() {
                function_mismatches += 1;
                push_mismatch(
                    format!("modules/{module_name}/functions/{fname}/params"),
                    format!(
                        "param count mismatch (rpc={} bytecode={})",
                        rpc_params.len(),
                        byte_params.len()
                    ),
                    rpc_fun.get("parameters").cloned(),
                    byte_fun.get("params").cloned(),
                );
            } else {
                for (i, (rp, bp)) in rpc_params.iter().zip(byte_params.iter()).enumerate() {
                    let rcanon = rpc_type_to_canonical_json(rp);
                    let bcanon = bytecode_type_to_canonical_json(bp);
                    match (rcanon, bcanon) {
                        (Ok(mut r), Ok(mut b)) => {
                            canonicalize_json_value(&mut r);
                            canonicalize_json_value(&mut b);
                            if r != b {
                                function_mismatches += 1;
                                push_mismatch(
                                    format!("modules/{module_name}/functions/{fname}/params[{i}]"),
                                    "param type mismatch".to_string(),
                                    Some(r),
                                    Some(b),
                                );
                            }
                        }
                        (Err(e), _) => {
                            function_mismatches += 1;
                            push_mismatch(
                                format!("modules/{module_name}/functions/{fname}/params[{i}]"),
                                format!("rpc type parse error: {:#}", e),
                                Some(rp.clone()),
                                None,
                            );
                        }
                        (_, Err(e)) => {
                            function_mismatches += 1;
                            push_mismatch(
                                format!("modules/{module_name}/functions/{fname}/params[{i}]"),
                                format!("bytecode type parse error: {:#}", e),
                                None,
                                Some(bp.clone()),
                            );
                        }
                    }
                }
            }

            let rpc_rets = rpc_fun
                .get("return")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default();
            let byte_rets = byte_fun
                .get("returns")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default();
            if rpc_rets.len() != byte_rets.len() {
                function_mismatches += 1;
                push_mismatch(
                    format!("modules/{module_name}/functions/{fname}/returns"),
                    format!(
                        "return count mismatch (rpc={} bytecode={})",
                        rpc_rets.len(),
                        byte_rets.len()
                    ),
                    rpc_fun.get("return").cloned(),
                    byte_fun.get("returns").cloned(),
                );
            } else {
                for (i, (rr, br)) in rpc_rets.iter().zip(byte_rets.iter()).enumerate() {
                    let rcanon = rpc_type_to_canonical_json(rr);
                    let bcanon = bytecode_type_to_canonical_json(br);
                    match (rcanon, bcanon) {
                        (Ok(mut r), Ok(mut b)) => {
                            canonicalize_json_value(&mut r);
                            canonicalize_json_value(&mut b);
                            if r != b {
                                function_mismatches += 1;
                                push_mismatch(
                                    format!("modules/{module_name}/functions/{fname}/returns[{i}]"),
                                    "return type mismatch".to_string(),
                                    Some(r),
                                    Some(b),
                                );
                            }
                        }
                        (Err(e), _) => {
                            function_mismatches += 1;
                            push_mismatch(
                                format!("modules/{module_name}/functions/{fname}/returns[{i}]"),
                                format!("rpc type parse error: {:#}", e),
                                Some(rr.clone()),
                                None,
                            );
                        }
                        (_, Err(e)) => {
                            function_mismatches += 1;
                            push_mismatch(
                                format!("modules/{module_name}/functions/{fname}/returns[{i}]"),
                                format!("bytecode type parse error: {:#}", e),
                                None,
                                Some(br.clone()),
                            );
                        }
                    }
                }
            }
        }
    }

    (
        InterfaceCompareSummary {
            modules_compared,
            modules_missing_in_bytecode: modules_missing_in_bytecode.len(),
            modules_extra_in_bytecode: modules_extra_in_bytecode.len(),
            structs_compared,
            struct_mismatches,
            functions_compared,
            function_mismatches,
            mismatches_total: mismatch_count_total,
        },
        mismatches,
    )
}

pub fn bytecode_module_check(
    normalized_module_names: &[String],
    bcs_module_names: &[String],
) -> BytecodeModuleCheck {
    let normalized_set: HashSet<&str> =
        normalized_module_names.iter().map(|s| s.as_str()).collect();
    let bcs_set: HashSet<&str> = bcs_module_names.iter().map(|s| s.as_str()).collect();

    let mut missing_in_bcs: Vec<String> = normalized_module_names
        .iter()
        .filter(|name| !bcs_set.contains(name.as_str()))
        .cloned()
        .collect();
    missing_in_bcs.sort();

    let mut extra_in_bcs: Vec<String> = bcs_module_names
        .iter()
        .filter(|name| !normalized_set.contains(name.as_str()))
        .cloned()
        .collect();
    extra_in_bcs.sort();

    BytecodeModuleCheck {
        normalized_modules: normalized_module_names.len(),
        bcs_modules: bcs_module_names.len(),
        missing_in_bcs,
        extra_in_bcs,
    }
}

pub fn module_set_diff(left: &[String], right: &[String]) -> ModuleSetDiff {
    let left_set: HashSet<&str> = left.iter().map(|s| s.as_str()).collect();
    let right_set: HashSet<&str> = right.iter().map(|s| s.as_str()).collect();

    let mut missing_in_right: Vec<String> = left
        .iter()
        .filter(|name| !right_set.contains(name.as_str()))
        .cloned()
        .collect();
    missing_in_right.sort();

    let mut extra_in_right: Vec<String> = right
        .iter()
        .filter(|name| !left_set.contains(name.as_str()))
        .cloned()
        .collect();
    extra_in_right.sort();

    ModuleSetDiff {
        left_count: left.len(),
        right_count: right.len(),
        missing_in_right,
        extra_in_right,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_compare_interface_rpc_vs_bytecode_smoke_ok() {
        let rpc = serde_json::json!({
            "modules": {
                "m": {
                    "structs": {
                        "S": {
                            "abilities": { "abilities": ["Store"] },
                            "typeParameters": [],
                            "fields": [
                                {"name":"x", "type":"U64"}
                            ]
                        }
                    },
                    "exposedFunctions": {
                        "f": {
                            "visibility":"Public",
                            "isEntry": false,
                            "typeParameters": [],
                            "parameters": ["U64"],
                            "return": []
                        }
                    }
                }
            }
        });

        let bytecode = serde_json::json!({
            "modules": {
                "m": {
                    "address": "0x0000000000000000000000000000000000000000000000000000000000000001",
                    "structs": {
                        "S": {
                            "abilities": ["store"],
                            "type_params": [],
                            "is_native": false,
                            "fields": [{"name":"x", "type": {"kind":"u64"}}]
                        }
                    },
                    "functions": {
                        "f": {
                            "visibility": "public",
                            "is_entry": false,
                            "is_native": false,
                            "type_params": [],
                            "params": [{"kind":"u64"}],
                            "returns": [],
                            "acquires": []
                        }
                    }
                }
            }
        });

        let (summary, mismatches) = compare_interface_rpc_vs_bytecode(
            "0x1",
            &rpc,
            &bytecode,
            InterfaceCompareOptions {
                max_mismatches: 10,
                include_values: true,
            },
        );
        assert_eq!(summary.mismatches_total, 0, "{mismatches:#?}");
        assert!(mismatches.is_empty());
    }

    #[test]
    fn test_compare_interface_rpc_vs_bytecode_detects_type_mismatch() {
        let rpc = serde_json::json!({
            "modules": {
                "m": {
                    "structs": {
                        "S": {
                            "abilities": { "abilities": ["Store"] },
                            "typeParameters": [],
                            "fields": [{"name":"x", "type":"U64"}]
                        }
                    },
                    "exposedFunctions": {}
                }
            }
        });

        let bytecode = serde_json::json!({
            "modules": {
                "m": {
                    "address": "0x1",
                    "structs": {
                        "S": {
                            "abilities": ["store"],
                            "type_params": [],
                            "is_native": false,
                            "fields": [{"name":"x", "type": {"kind":"u128"}}]
                        }
                    },
                    "functions": {}
                }
            }
        });

        let (summary, mismatches) = compare_interface_rpc_vs_bytecode(
            "0x1",
            &rpc,
            &bytecode,
            InterfaceCompareOptions {
                max_mismatches: 10,
                include_values: false,
            },
        );
        assert!(summary.mismatches_total > 0);
        assert!(mismatches
            .iter()
            .any(|m| m.path.contains("/fields[0]/type")));
        assert!(mismatches
            .iter()
            .all(|m| m.rpc.is_none() && m.bytecode.is_none()));
    }
}
