# Bug Report: `update_project_item_field` Fails for 'Number' and 'Date' Fields

This document outlines a bug in the `update_project_item_field` tool where it fails to update custom fields of type 'Number' and 'Date' in a GitHub Project.

## 1. Problem Description

The `update_project_item_field` tool consistently fails when attempting to update the values of custom fields with the types 'Number' and 'Date'. The tool successfully updates fields of type 'SingleSelect', but any attempt to update the other two types results in a generic error: `Error: Could not update field value. Details: Failed to update field value for item ...`.

This prevents the automation of key project management data, such as setting story points and start/target dates for project items.

## 2. Project Context for Testing

This section provides all the necessary details to reproduce and test the issue using a real-world project setup.

### Project Details

```json
{
  "id": "PVT_kwHOAAW1i84BADGg",
  "number": 3,
  "title": "BranchChat: Development",
  "owner": "mweichert",
  "url": "https://github.com/users/mweichert/projects/3"
}
```

### Test Item (Issue #1)

- **Issue Number:** 1
- **Repository:** `mweichert/BranchChat`
- **Item ID:** `PVTI_lAHOAAW1i84BADGgzgdd8ew`

### Custom Field Definitions

```json
[
  {
    "name": "Story Points",
    "id": "PVTF_lAHOAAW1i84BADGgzgy-kZs",
    "type": "ProjectV2Field" 
  },
  {
    "name": "Start Date",
    "id": "PVTF_lAHOAAW1i84BADGgzgy-JI8",
    "type": "ProjectV2Field"
  },
  {
    "name": "Target Date",
    "id": "PVTF_lAHOAAW1i84BADGgzgy-JLg",
    "type": "ProjectV2Field"
  },
  {
    "name": "Priority",
    "id": "PVTSSF_lAHOAAW1i84BADGgzgy-JI4",
    "type": "ProjectV2SingleSelectField",
    "options": [
      { "name": "Critical", "id": "06b11da1" }
    ]
  }
]
```

## 3. Summary of Failed Attempts

The following is a log of the different `field_value` formats that have been attempted and have failed for the 'Number' and 'Date' field types.

### For "Story Points" (Number Field)

- **As a string:** `"64"`
- **As a number:** `64` (This resulted in an unparsable response from the tool)

### For "Start Date" and "Target Date" (Date Fields)

- **YYYY-MM-DD:** `"2025-08-11"`
- **ISO 8601 Timestamp:** `"2025-08-11T00:00:00Z"`
- **Unix Timestamp:** `"1754892800"`
- **Human-readable string:** `"Aug 11, 2025"`

## 4. Proposed Testing Plan

This plan outlines the steps to reproduce the bug and verify the fix.

### Step 1: Reproduce the Bug

1.  **Target the "Story Points" field.**
    - Execute the `update_project_item_field` tool with the following parameters:
      - `owner`: `"mweichert"`
      - `project_number`: `3`
      - `item_id`: `"PVTI_lAHOAAW1i84BADGgzgdd8ew"`
      - `field_id`: `"PVTF_lAHOAAW1i84BADGgzgy-kZs"`
      - `field_value`: `"64"`
    - **Expected Result:** The tool should return an error.

2.  **Target the "Start Date" field.**
    - Execute the `update_project_item_field` tool with the following parameters:
      - `owner`: `"mweichert"`
      - `project_number`: `3`
      - `item_id`: `"PVTI_lAHOAAW1i84BADGgzgdd8ew"`
      - `field_id`: `"PVTF_lAHOAAW1i84BADGgzgy-JI8"`
      - `field_value`: `"2025-08-11"`
    - **Expected Result:** The tool should return an error.

### Step 2: Test the Fix

After implementing a potential fix in the `github-projects-mcp` codebase, the following tests should be run.

1.  **Test the "Story Points" field.**
    - Execute the same command as in Step 1.1.
    - **Expected Result:** The tool should succeed and return a confirmation message. The "Story Points" field for issue #1 in the "BranchChat: Development" project should be updated to `64`.

2.  **Test the "Start Date" field.**
    - Execute the same command as in Step 1.2.
    - **Expected Result:** The tool should succeed. The "Start Date" field for issue #1 should be updated to `2025-08-11`.

3.  **Test the "Target Date" field.**
    - Execute the `update_project_item_field` tool with `field_id`: `"PVTF_lAHOAAW1i84BADGgzgy-JLg"` and `field_value`: `"2025-09-19"`.
    - **Expected Result:** The tool should succeed. The "Target Date" field for issue #1 should be updated to `2025-09-19`.

4.  **Verify SingleSelect Fields Still Work.**
    - Execute the `update_project_item_field` tool to update the "Priority" field:
      - `field_id`: `"PVTSSF_lAHOAAW1i84BADGgzgy-JI4"`
      - `field_value`: `"06b11da1"` (ID for "Critical")
    - **Expected Result:** The tool should succeed, confirming that the fix did not break existing functionality.
