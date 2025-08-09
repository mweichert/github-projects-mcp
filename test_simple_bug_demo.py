#!/usr/bin/env python3
"""
Simple demonstration of the field update bug.

This script shows how the current field type detection logic fails
for Number and Date fields that have PVTF_ prefixes.
"""

def demonstrate_field_type_detection_bug():
    """
    Demonstrates the core bug in field type detection logic.
    
    The issue is in github_client.py lines 1017-1058 where field types
    are determined by ID prefixes, but the real-world data shows that
    Number and Date fields can also have PVTF_ prefixes.
    """
    
    print("=== Demonstrating Field Type Detection Bug ===\n")
    
    # Real field data from github-projects-mcp-issue.md
    test_fields = [
        {
            "name": "Story Points",
            "id": "PVTF_lAHOAAW1i84BADGgzgy-kZs",
            "actual_type": "Number",
            "test_value": "64"
        },
        {
            "name": "Start Date", 
            "id": "PVTF_lAHOAAW1i84BADGgzgy-JI8",
            "actual_type": "Date",
            "test_value": "2025-08-11"
        },
        {
            "name": "Priority",
            "id": "PVTSSF_lAHOAAW1i84BADGgzgy-JI4", 
            "actual_type": "SingleSelect",
            "test_value": "06b11da1"
        }
    ]
    
    print("Current buggy logic in update_project_item_field:")
    print("=" * 50)
    
    for field in test_fields:
        field_id = field["id"]
        actual_type = field["actual_type"]
        test_value = field["test_value"]
        
        # Replicate the buggy logic from github_client.py:1017-1058
        if field_id.startswith("PVTSSF_"):  # Single Select Field
            detected_type = "SingleSelect"
            field_value_input = {"singleSelectOptionId": test_value}
        elif field_id.startswith("PVTF_"):  # Text Field (WRONG ASSUMPTION!)
            detected_type = "Text"
            field_value_input = {"text": str(test_value)}
        elif field_id.startswith("PVTDF_"):  # Date Field
            detected_type = "Date" 
            field_value_input = {"date": test_value}
        elif field_id.startswith("PVTNU_"):  # Number Field
            detected_type = "Number"
            field_value_input = {"number": float(test_value)}
        else:
            detected_type = "Text (default)"
            field_value_input = {"text": str(test_value)}
        
        status = "✅ CORRECT" if detected_type.split()[0] == actual_type else "❌ WRONG"
        
        print(f"Field: {field['name']}")
        print(f"  ID: {field_id}")
        print(f"  Actual Type: {actual_type}")
        print(f"  Detected Type: {detected_type}")
        print(f"  Generated Input: {field_value_input}")
        print(f"  Status: {status}")
        
        if "WRONG" in status:
            if actual_type == "Number":
                correct_input = {"number": float(test_value)}
                print(f"  Should be: {correct_input}")
            elif actual_type == "Date":
                correct_input = {"date": test_value}
                print(f"  Should be: {correct_input}")
        print()
    
    print("Root Cause:")
    print("=" * 50) 
    print("The bug occurs because the code assumes that field ID prefixes")
    print("reliably indicate field types, but this is not true in practice.")
    print("Both 'Story Points' (Number) and 'Start Date' (Date) fields")
    print("have IDs starting with 'PVTF_', causing them to be incorrectly")
    print("treated as Text fields.")
    print()
    print("This results in GraphQL mutations with wrong field value types:")
    print("- Number fields get {\"text\": \"64\"} instead of {\"number\": 64.0}")
    print("- Date fields get {\"text\": \"2025-08-11\"} instead of {\"date\": \"2025-08-11\"}")
    print()
    print("The fix requires fetching actual field types from the GraphQL API")
    print("rather than guessing based on ID prefixes.")

if __name__ == "__main__":
    demonstrate_field_type_detection_bug()