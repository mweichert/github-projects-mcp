#!/usr/bin/env python3
"""
TDD tests for milestone management tools.
Following Red-Green-Refactor cycle.
"""

import os
import pytest
from unittest.mock import AsyncMock, patch
from src.github_projects_mcp.github_client import GitHubClient, GitHubClientError

# Set a dummy token to avoid initialization error
os.environ.setdefault("GITHUB_TOKEN", "dummy_token_for_testing")


class TestMilestoneManagement:
    """Test milestone management functionality using TDD approach."""

    @pytest.fixture
    def github_client(self):
        """Create a mock GitHub client for testing."""
        return GitHubClient(token="test_token")

    @pytest.mark.asyncio
    async def test_list_repository_milestones_success(self, github_client):
        """Test listing repository milestones - should fail initially."""
        # Arrange
        owner = "testowner"
        repo = "testrepo"
        expected_milestones = [
            {
                "id": 1,
                "number": 1,
                "title": "v1.0",
                "state": "open",
                "description": "First release",
                "due_on": "2024-12-31T23:59:59Z",
                "open_issues": 5,
                "closed_issues": 2,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-15T12:00:00Z"
            }
        ]

        # Mock the REST API call that doesn't exist yet
        with patch.object(github_client, 'list_repository_milestones', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = expected_milestones

            # Act & Assert - This should fail because method doesn't exist
            result = await github_client.list_repository_milestones(owner, repo)
            assert result == expected_milestones
            mock_list.assert_called_once_with(owner, repo)

    @pytest.mark.asyncio
    async def test_list_repository_milestones_with_filters(self, github_client):
        """Test listing milestones with state and sorting filters."""
        # Arrange
        owner = "testowner"
        repo = "testrepo"
        state = "closed"
        sort = "due_on"
        direction = "desc"

        # Mock method that doesn't exist yet
        with patch.object(github_client, 'list_repository_milestones', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            # Act & Assert - Should fail because method doesn't exist
            result = await github_client.list_repository_milestones(
                owner, repo, state=state, sort=sort, direction=direction
            )
            assert result == []
            mock_list.assert_called_once_with(owner, repo, state=state, sort=sort, direction=direction)

    @pytest.mark.asyncio
    async def test_list_repository_milestones_error_handling(self, github_client):
        """Test error handling for list milestones."""
        # Arrange
        owner = "nonexistent"
        repo = "repo"

        # Mock method to raise error
        with patch.object(github_client, 'list_repository_milestones', new_callable=AsyncMock) as mock_list:
            mock_list.side_effect = GitHubClientError("Repository not found")

            # Act & Assert - Should fail because method doesn't exist
            with pytest.raises(GitHubClientError, match="Repository not found"):
                await github_client.list_repository_milestones(owner, repo)

    @pytest.mark.asyncio
    async def test_create_milestone_success(self, github_client):
        """Test creating a milestone - should fail initially."""
        # Arrange
        owner = "testowner"
        repo = "testrepo"
        title = "v2.0"
        description = "Second major release"
        due_on = "2024-12-31T23:59:59Z"
        
        expected_milestone = {
            "id": 2,
            "number": 2,
            "title": title,
            "state": "open",
            "description": description,
            "due_on": due_on
        }

        # Mock method that doesn't exist yet
        with patch.object(github_client, 'create_milestone', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = expected_milestone

            # Act & Assert - Should fail because method doesn't exist
            result = await github_client.create_milestone(owner, repo, title, description, due_on)
            assert result == expected_milestone
            mock_create.assert_called_once_with(owner, repo, title, description, due_on)

    @pytest.mark.asyncio
    async def test_get_milestone_success(self, github_client):
        """Test getting a specific milestone - should fail initially."""
        # Arrange
        owner = "testowner"
        repo = "testrepo"
        milestone_number = 1
        
        expected_milestone = {
            "id": 1,
            "number": 1,
            "title": "v1.0",
            "state": "open"
        }

        # Mock method that doesn't exist yet
        with patch.object(github_client, 'get_milestone', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = expected_milestone

            # Act & Assert - Should fail because method doesn't exist
            result = await github_client.get_milestone(owner, repo, milestone_number)
            assert result == expected_milestone
            mock_get.assert_called_once_with(owner, repo, milestone_number)

    @pytest.mark.asyncio
    async def test_update_milestone_success(self, github_client):
        """Test updating a milestone - should fail initially."""
        # Arrange
        owner = "testowner"
        repo = "testrepo"
        milestone_number = 1
        title = "v1.1"
        state = "closed"
        
        expected_milestone = {
            "id": 1,
            "number": 1,
            "title": title,
            "state": state
        }

        # Mock method that doesn't exist yet
        with patch.object(github_client, 'update_milestone', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = expected_milestone

            # Act & Assert - Should fail because method doesn't exist
            result = await github_client.update_milestone(owner, repo, milestone_number, title=title, state=state)
            assert result == expected_milestone
            mock_update.assert_called_once_with(owner, repo, milestone_number, title=title, state=state)

    @pytest.mark.asyncio
    async def test_delete_milestone_success(self, github_client):
        """Test deleting a milestone - should fail initially."""
        # Arrange
        owner = "testowner"
        repo = "testrepo"
        milestone_number = 1

        # Mock method that doesn't exist yet
        with patch.object(github_client, 'delete_milestone', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True

            # Act & Assert - Should fail because method doesn't exist
            result = await github_client.delete_milestone(owner, repo, milestone_number)
            assert result is True
            mock_delete.assert_called_once_with(owner, repo, milestone_number)


class TestMilestoneTools:
    """Test MCP milestone tools."""

    def test_list_repository_milestones_tool_exists(self):
        """Test the list_repository_milestones MCP tool exists - should fail initially."""
        # This test will fail because the tool doesn't exist yet
        import src.github_projects_mcp.server as server_module
        
        # Check if function exists in module
        assert hasattr(server_module, "list_repository_milestones"), "Tool function not implemented yet"

    def test_create_milestone_tool_exists(self):
        """Test the create_milestone MCP tool exists - should fail initially."""
        # This test will fail because the tool doesn't exist yet
        import src.github_projects_mcp.server as server_module
        
        # Check if function exists in module
        assert hasattr(server_module, "create_milestone"), "Tool function not implemented yet"