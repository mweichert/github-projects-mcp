# Analysis of `update_project_item_field` Bug

This document provides an analysis of the bug affecting the `update_project_item_field` tool and outlines a proposed solution.

## 1. Root Cause Analysis

The root cause of the bug lies in the `update_project_item_field` function within `src/github_projects_mcp/github_client.py`. The current implementation attempts to determine the data type of a project field by using a heuristic based on the prefix of the `field_id`.

Specifically, the code contains the following logic:

```python
# src/github_projects_mcp/github_client.py

if field_id.startswith("PVTSSF_"):  # Single Select Field
    field_value_input = {"singleSelectOptionId": value}
elif field_id.startswith("PVTF_"):  # Text Field (assumed prefix)
    field_value_input = {"text": str(value)}
elif field_id.startswith("PVTDF_"):  # Date Field (assumed prefix)
    field_value_input = {"date": value}
elif field_id.startswith("PVTNU_"):  # Number Field (assumed prefix)
    field_value_input = {"number": float(value)}
else:  # Default to text if type unknown
    field_value_input = {"text": str(value)}
```

This approach is unreliable because the field ID prefixes are not guaranteed to correspond to the field's data type. As revealed in the bug report, the "Story Points" (Number) and "Start Date" (Date) fields both have IDs starting with `PVTF_`, which the code incorrectly assumes is always a "Text" field.

When the tool attempts to update a "Number" or "Date" field, it constructs the GraphQL mutation with a `{ "text": "..." }` payload, which is invalid for those field types, causing the GitHub API to return an error.

The `update_project_item_field` tool in `src/github_projects_mcp/server.py` also contributes to the problem by performing only basic type inference on the `field_value` before passing it to the `github_client`.

## 2. Proposed Solution

To fix this bug, the system must be updated to reliably determine the correct data type for a given field before constructing the GraphQL mutation. The guessing logic based on ID prefixes must be replaced with a more robust mechanism.

The proposed solution involves the following steps:

1.  **Enhance Field Discovery:** The `get_project_fields_details` function in `github_client.py` currently retrieves the `__typename` for each field. However, for fields of type `ProjectV2Field`, it does not differentiate between "Text", "Number", and "Date". The GraphQL query within this function needs to be updated to fetch the `dataType` for each field.

    The updated query should look like this:

    ```graphql
    query GetProjectFields($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          fields(first: 50) {
            nodes {
              ... on ProjectV2Field { id name __typename dataType } # <-- Add dataType
              ... on ProjectV2IterationField {
                 id name __typename
                 configuration { iterations { id title startDate duration } }
              }
              ... on ProjectV2SingleSelectField {
                 id name __typename
                 options { id name color description }
              }
            }
          }
        }
      }
    }
    ```

2.  **Refactor `update_project_item_field`:** The `update_project_item_field` function in `github_client.py` must be refactored to:
    a.  Call `get_project_fields_details` to get the complete details for all fields in the project.
    b.  Find the specific field being updated using the `field_id`.
    c.  Use the `dataType` and `__typename` from the field details to determine the correct structure for the `ProjectV2FieldValue` input object.
    d.  Construct the GraphQL mutation with the correctly typed value (e.g., `{"number": 64}` or `{"date": "2025-08-11"}`).

3.  **Improve Value Parsing:** The `update_project_item_field` tool in `server.py` should be updated to intelligently parse the incoming `field_value` string based on the determined data type. For example, it should convert the value to a `float` if the field type is "NUMBER".

## 3. Implementation Plan

1.  **Modify `github_client.py`:**
    - Update the GraphQL query in `get_project_fields_details` to include `dataType`.
    - Modify the processing loop in `get_project_fields_details` to store the `dataType`.
    - Rewrite the `update_project_item_field` function to fetch field details and build the mutation payload based on the actual `dataType`.

2.  **Modify `server.py`:**
    - Update the `update_project_item_field` tool to perform type conversion on `field_value` based on the field's type before calling the `github_client`. This may involve a preliminary call to a function that can determine the field type by its ID.

This approach will eliminate the unreliable guesswork and ensure that the GraphQL mutations are always constructed with the correct data types, resolving the bug for "Number" and "Date" fields while maintaining functionality for "SingleSelect" and other field types.
