#!/usr/bin/env python3
"""
Simple test to verify the fix works by inspecting the actual call structure.
"""

import asyncio
from unittest.mock import AsyncMock, patch
from src.github_projects_mcp.github_client import GitHubClient


async def test_fix_works():
    """Verify the fix generates correct field value inputs."""
    client = GitHubClient(token="fake_token")
    
    # Mock field details with correct types
    mock_field_details = {
        "Story Points": {
            "id": "PVTF_lAHOAAW1i84BADGgzgy-kZs",
            "type": "ProjectV2Field",
            "dataType": "NUMBER",
            "options": {},
            "iterations": {}
        },
        "Start Date": {
            "id": "PVTF_lAHOAAW1i84BADGgzgy-JI8",
            "type": "ProjectV2Field", 
            "dataType": "DATE",
            "options": {},
            "iterations": {}
        },
        "Priority": {
            "id": "PVTSSF_lAHOAAW1i84BADGgzgy-JI4",
            "type": "ProjectV2SingleSelectField",
            "dataType": None,
            "options": {"Critical": "06b11da1"},
            "iterations": {}
        }
    }
    
    with patch.object(client, 'get_project_node_id', return_value="PVT_kwHOAAW1i84BADGg"), \
         patch.object(client, 'get_project_fields_details', return_value=mock_field_details), \
         patch.object(client, 'execute_query', return_value={"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": "test"}}}) as mock_execute:
        
        print("Testing Number field...")
        await client.update_project_item_field(
            owner="mweichert",
            project_number=3,
            item_id="PVTI_lAHOAAW1i84BADGgzgdd8ew",
            field_id="PVTF_lAHOAAW1i84BADGgzgy-kZs",  # Story Points
            value="64"
        )
        
        # Check the mutation call
        calls = mock_execute.call_args_list
        print(f"All calls: {calls}")
        mutation_call = calls[-1]  # Last call should be the mutation
        print(f"Mutation call structure: {mutation_call}")
        print(f"Call args: {mutation_call[0] if mutation_call else 'None'}")
        print(f"Call kwargs: {mutation_call[1] if len(mutation_call) > 1 else 'None'}")
        
        # Access the variables from the call arguments
        # The call structure is call(query_string, variables_dict)
        variables = mutation_call.args[1] if len(mutation_call.args) > 1 else {}
        
        print(f"Number field value: {variables.get('value')}")
        assert variables.get('value') == {"number": 64.0}, f"Expected number field but got {variables.get('value')}"
        print("✅ Number field correctly generates {'number': 64.0}")
        
        # Reset mock
        mock_execute.reset_mock()
        
        print("\nTesting Date field...")
        await client.update_project_item_field(
            owner="mweichert",
            project_number=3,
            item_id="PVTI_lAHOAAW1i84BADGgzgdd8ew",
            field_id="PVTF_lAHOAAW1i84BADGgzgy-JI8",  # Start Date
            value="2025-08-11"
        )
        
        calls = mock_execute.call_args_list
        mutation_call = calls[-1]
        variables = mutation_call.args[1] if len(mutation_call.args) > 1 else {}
        
        print(f"Date field value: {variables.get('value')}")
        assert variables.get('value') == {"date": "2025-08-11"}, f"Expected date field but got {variables.get('value')}"
        print("✅ Date field correctly generates {'date': '2025-08-11'}")
        
        # Reset mock
        mock_execute.reset_mock()
        
        print("\nTesting SingleSelect field...")
        await client.update_project_item_field(
            owner="mweichert", 
            project_number=3,
            item_id="PVTI_lAHOAAW1i84BADGgzgdd8ew",
            field_id="PVTSSF_lAHOAAW1i84BADGgzgy-JI4",  # Priority
            value="06b11da1"
        )
        
        calls = mock_execute.call_args_list
        mutation_call = calls[-1]
        variables = mutation_call.args[1] if len(mutation_call.args) > 1 else {}
        
        print(f"SingleSelect field value: {variables.get('value')}")
        assert variables.get('value') == {"singleSelectOptionId": "06b11da1"}, f"Expected single select field but got {variables.get('value')}"
        print("✅ SingleSelect field correctly generates {'singleSelectOptionId': '06b11da1'}")


if __name__ == "__main__":
    print("=== Testing the Bug Fix ===\n")
    asyncio.run(test_fix_works())
    print("\n🎉 All tests passed! The fix is working correctly.")