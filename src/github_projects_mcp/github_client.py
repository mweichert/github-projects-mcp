"""
GitHub GraphQL API client for the GitHub Projects V2 MCP Server.
"""

import base64
import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx
from nacl import public, encoding

logger = logging.getLogger(__name__)


class GitHubClientError(Exception):
    """Custom exception for GitHubClient errors."""

    pass


class GitHubClient:
    """Client for interacting with the GitHub GraphQL API."""

    def __init__(self, token: Optional[str] = None):
        """Initialize the GitHub client.

        Args:
            token: GitHub personal access token. If None, it will use the GITHUB_TOKEN env var.
        """
        self.token = token or os.environ.get("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GitHub token is required")

        self.api_url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github.v4+json",
        }

    def _find_case_insensitive_key(
        self, dictionary: Dict[str, Any], key: str
    ) -> Optional[str]:
        """Find a key in a dictionary case-insensitively.

        Args:
            dictionary: Dictionary to search in
            key: Key to find (case-insensitive)

        Returns:
            The actual key if found, None otherwise
        """
        if not key:
            return None

        for dict_key in dictionary:
            if dict_key and key and dict_key.lower() == key.lower():
                return dict_key
        return None

    def encrypt_secret_value(self, secret_value: str, public_key: str) -> str:
        """Encrypt a secret value using LibSodium public key encryption.

        Args:
            secret_value: The plaintext secret value to encrypt
            public_key: Base64-encoded public key from GitHub

        Returns:
            Base64-encoded encrypted value

        Raises:
            ValueError: If public key is invalid or encryption fails
        """
        try:
            # Decode the base64 public key
            public_key_bytes = base64.b64decode(public_key)
            
            # Create PyNaCl public key object
            public_key_obj = public.PublicKey(public_key_bytes)
            
            # Create sealed box for encryption
            sealed_box = public.SealedBox(public_key_obj)
            
            # Encrypt the secret value
            encrypted = sealed_box.encrypt(secret_value.encode('utf-8'))
            
            # Return base64-encoded encrypted value
            return base64.b64encode(encrypted).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to encrypt secret value: {e}")
            raise ValueError(f"Invalid public key format or encryption failed: {e}") from e

    async def execute_query(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a GraphQL query against the GitHub API.

        Args:
            query: The GraphQL query string
            variables: Variables for the GraphQL query

        Returns:
            The parsed JSON response data

        Raises:
            GitHubClientError: If the query fails or returns errors.
        """
        query_variables = variables or {}

        payload = {"query": query, "variables": query_variables}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url, headers=self.headers, json=payload, timeout=30.0
                )
                response.raise_for_status()  # Raise HTTP errors
                result = response.json()

                # Check for errors AND the presence of data
                if "errors" in result:
                    data = result.get("data")
                    if data is None:
                        # No data returned, errors are fatal
                        error_message = f"GraphQL query failed with errors and returned no data: {result['errors']}"
                        logger.error(error_message)
                        raise GitHubClientError(error_message)
                    else:
                        # Data IS present, log errors as warnings but proceed
                        logger.warning(
                            f"GraphQL query returned errors but also data: {result['errors']}"
                        )

                # If we reach here, either there were no errors, or there were errors but also data.
                data = result.get("data")
                if data is None:
                    # This case should now only happen if there were no errors but still no data.
                    raise GitHubClientError(
                        "GraphQL query returned no data and no errors."
                    )

                return data  # Return data
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error executing GraphQL query: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error executing GraphQL query: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def get_projects(self, owner: str) -> List[Dict[str, Any]]:
        """Get Projects V2 for an organization or user.

        Args:
            owner: The GitHub organization or user name

        Returns:
            List of projects

        Raises:
            GitHubClientError: If the owner is not found or projects cannot be retrieved.
        """
        # First determine if this is a user or organization
        query = """
        query GetOwnerType($login: String!) {
          organization(login: $login) {
            id
            login
            __typename
          }
          user(login: $login) {
            id
            login
            __typename
          }
        }
        """

        variables = {"login": owner}

        try:
            result = await self.execute_query(query, variables)
        except GitHubClientError as e:
            logger.error(f"Failed to determine owner type for {owner}: {e}")
            raise  # Re-raise the error

        # Determine if the owner is a user or organization
        owner_type = None
        owner_id = None

        if result.get("organization"):
            owner_type = "organization"
            owner_id = result["organization"]["id"]
        elif result.get("user"):
            owner_type = "user"
            owner_id = result["user"]["id"]
        else:
            error_message = f"Owner {owner} not found or type could not be determined."
            logger.error(error_message)
            raise GitHubClientError(error_message)

        # Now get the projects based on owner type
        if owner_type == "organization":
            query = """
            query GetOrgProjects($login: String!, $first: Int!) {
              organization(login: $login) {
                projectsV2(first: $first) {
                  nodes {
                    id
                    number
                    title
                    shortDescription
                    url
                    closed
                    public
                  }
                }
              }
            }
            """

            variables = {"login": owner, "first": 50}

            try:
                result = await self.execute_query(query, variables)
                if not result.get("organization") or not result["organization"].get(
                    "projectsV2"
                ):
                    raise GitHubClientError(
                        f"Could not retrieve projects for organization {owner}"
                    )
                return result["organization"]["projectsV2"]["nodes"]
            except GitHubClientError as e:
                logger.error(f"Failed to get projects for organization {owner}: {e}")
                raise

        elif owner_type == "user":
            query = """
            query GetUserProjects($login: String!, $first: Int!) {
              user(login: $login) {
                projectsV2(first: $first) {
                  nodes {
                    id
                    number
                    title
                    shortDescription
                    url
                    closed
                    public
                  }
                }
              }
            }
            """

            variables = {"login": owner, "first": 50}

            try:
                result = await self.execute_query(query, variables)
                if not result.get("user") or not result["user"].get("projectsV2"):
                    raise GitHubClientError(
                        f"Could not retrieve projects for user {owner}"
                    )
                return result["user"]["projectsV2"]["nodes"]
            except GitHubClientError as e:
                logger.error(f"Failed to get projects for user {owner}: {e}")
                raise

        # This part should be unreachable if owner_type is determined correctly
        raise GitHubClientError(f"Unexpected error retrieving projects for {owner}")

    async def get_project_node_id(self, owner: str, project_number: int) -> str:
        """Get the node ID of a project.

        Args:
            owner: The GitHub organization or user name
            project_number: The project number

        Returns:
            The project node ID

        Raises:
            GitHubClientError: If the project is not found.
        """
        # First determine if this is a user or organization
        query = """
        query GetProjectId($login: String!, $number: Int!) {
          organization(login: $login) {
            projectV2(number: $number) {
              id
            }
          }
          user(login: $login) {
            projectV2(number: $number) {
              id
            }
          }
        }
        """

        variables = {"login": owner, "number": project_number}

        try:
            result = await self.execute_query(query, variables)
        except GitHubClientError as e:
            logger.error(
                f"Failed to query project ID for {owner}/{project_number}: {e}"
            )
            raise

        if result.get("organization") and result["organization"].get("projectV2"):
            return result["organization"]["projectV2"]["id"]
        elif result.get("user") and result["user"].get("projectV2"):
            return result["user"]["projectV2"]["id"]
        else:
            error_message = f"Project {project_number} not found for owner {owner}."
            logger.error(error_message)
            raise GitHubClientError(error_message)

    async def get_project_fields_details(
        self, owner: str, project_number: int
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get fields for a GitHub Project V2, returning a structured dictionary.
        Args:
            owner: The GitHub organization or user name
            project_number: The project number
        Returns:
            Dictionary mapping field name to its details (id, type, options).
        Raises:
            GitHubClientError: If project or fields cannot be retrieved.
        """
        try:
            project_id = await self.get_project_node_id(owner, project_number)
        except GitHubClientError as e:
            logger.error(f"Cannot get fields details: {e}")
            raise

        query = """
        query GetProjectFields($projectId: ID!) {
          node(id: $projectId) {
            ... on ProjectV2 {
              fields(first: 50) {
                nodes {
                  ... on ProjectV2Field { id name __typename dataType }
                  ... on ProjectV2IterationField {
                     id name __typename
                     configuration { iterations { id title startDate duration } }
                  }
                  ... on ProjectV2SingleSelectField {
                     id name __typename
                     options { id name color description }
                  }
                  # Add other field types if needed
                }
              }
            }
          }
        }
        """
        variables = {"projectId": project_id}

        try:
            result = await self.execute_query(query, variables)
            if not result.get("node") or not result["node"].get("fields"):
                raise GitHubClientError(
                    f"Could not retrieve fields for project {owner}/{project_number}"
                )

            fields_nodes = result["node"]["fields"]["nodes"]
            field_details_map: Dict[str, Dict[str, Any]] = {}
            for field in fields_nodes:
                field_name = field.get("name")
                if field_name:
                    options_map = {}
                    if field.get("options"):
                        options_map = {
                            opt["name"]: opt["id"] for opt in field["options"]
                        }
                    iterations_map = {}
                    if field.get(
                        "__typename"
                    ) == "ProjectV2IterationField" and field.get(
                        "configuration", {}
                    ).get(
                        "iterations"
                    ):
                        iterations = field.get("configuration", {}).get(
                            "iterations", []
                        )
                        iterations_map = {
                            iter["title"]: iter["id"] for iter in iterations
                        }

                    field_details_map[field_name] = {
                        "id": field.get("id"),
                        "type": field.get("__typename"),
                        "dataType": field.get("dataType"),  # Add dataType for ProjectV2Field
                        "options": options_map,  # Map Name -> ID
                        "iterations": iterations_map,
                    }
            return field_details_map
        except GitHubClientError as e:
            logger.error(
                f"Failed to get fields details for project {owner}/{project_number}: {e}"
            )
            raise
        except Exception as e:  # Catch potential errors during processing
            logger.error(
                f"Unexpected error processing fields for project {owner}/{project_number}: {e}"
            )
            raise GitHubClientError(
                f"Could not process fields for project {owner}/{project_number}"
            )

    async def get_project_items(
        self,
        owner: str,
        project_number: int,
        limit: int = 10,
        state: Optional[str] = None,
        filter_field_name: Optional[str] = None,
        filter_field_value: Optional[str] = None,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get items in a GitHub Project V2, optionally filtering by state or a custom field value.
        Args:
            owner: The GitHub organization or user name
            project_number: The project number
            limit: Maximum number of items to return per page (default: 10)
            state: Optional state to filter items by (e.g., "OPEN", "CLOSED").
            filter_field_name: Optional name of a custom field to filter by (e.g., "Status").
            filter_field_value: Optional value of the custom field to filter by (e.g., "Backlog").
            cursor: Optional cursor for pagination (default: None for first page)
        Returns:
            Dictionary containing:
                - items: List of project items
                - pageInfo: Information about pagination (hasNextPage, endCursor)
        Raises:
            GitHubClientError: If project or items cannot be retrieved, or filter is invalid.
            ValueError: If filter parameters are invalid.
        """
        try:
            project_id = await self.get_project_node_id(owner, project_number)
        except GitHubClientError as e:
            logger.error(f"Cannot get items: {e}")
            raise

        # When filtering, we need to fetch more items since many will be excluded
        # Increase the fetch size to be more efficient
        fetch_limit = limit
        if filter_field_name and filter_field_value:
            # Be more aggressive but respect GitHub's 100 record limit
            fetch_limit = min(max(limit * 5, 50), 100)
            logger.debug(
                f"Filtering enabled: increasing fetch limit from {limit} to {fetch_limit}"
            )

        # Prepare variables dict before use
        variables: Dict[str, Any] = {"projectId": project_id, "first": fetch_limit}

        # Add cursor if provided (for pagination)
        after_clause = ""
        if cursor:
            variables["cursor"] = cursor
            after_clause = ", after: $cursor"

        # Base query definition including fragments
        field_values_fragment = """
        fragment FieldValuesFragment on ProjectV2ItemFieldValueConnection {
            nodes {
               ... on ProjectV2ItemFieldTextValue { __typename text field { ... on ProjectV2FieldCommon { name } } }
               ... on ProjectV2ItemFieldDateValue { __typename date field { ... on ProjectV2FieldCommon { name } } }
               ... on ProjectV2ItemFieldSingleSelectValue { __typename name field { ... on ProjectV2FieldCommon { name } } }
               ... on ProjectV2ItemFieldNumberValue { __typename number field { ... on ProjectV2FieldCommon { name } } }
               ... on ProjectV2ItemFieldIterationValue { __typename title startDate duration field { ... on ProjectV2FieldCommon { name } } }
            }
        }
        """
        content_fragment = """
        fragment ContentFragment on ProjectV2ItemContent {
           ... on Issue { __typename id number title state url repository { name owner { login } } }
           ... on PullRequest { __typename id number title state url repository { name owner { login } } }
           ... on DraftIssue { __typename id title body }
        }
        """

        # Build filter parameters if needed
        filter_conditions = []

        if state:
            if state.upper() not in ["OPEN", "CLOSED"]:
                raise ValueError("Invalid state filter. Must be 'OPEN' or 'CLOSED'.")
            # For state filtering, let's collect all items and filter afterwards
            # as the API has changed how filtering works

        # Variables for field-based filtering
        field_id_var = None
        option_id_var = None

        if filter_field_name and filter_field_value:
            try:
                all_fields = await self.get_project_fields_details(
                    owner, project_number
                )
                logger.debug(f"All fields available: {list(all_fields.keys())}")

                # First try exact match
                field_info = all_fields.get(filter_field_name)
                # If not found, try case-insensitive match
                if not field_info:
                    actual_field_name = self._find_case_insensitive_key(
                        all_fields, filter_field_name
                    )
                    if actual_field_name:
                        field_info = all_fields.get(actual_field_name)
                        logger.info(
                            f"Found field '{actual_field_name}' using case-insensitive match for '{filter_field_name}'"
                        )

                if not field_info:
                    raise ValueError(f"Field '{filter_field_name}' not found.")
                field_id = field_info["id"]
                field_type = field_info["type"]

                logger.debug(
                    f"Found field '{filter_field_name}' with ID {field_id} and type {field_type}"
                )

                if field_type == "ProjectV2SingleSelectField":
                    available_options = list(field_info.get("options", {}).keys())
                    logger.debug(
                        f"Available options for '{filter_field_name}': {available_options}"
                    )

                    # First try exact match
                    option_id = field_info.get("options", {}).get(filter_field_value)
                    # If not found, try case-insensitive match
                    if not option_id:
                        options = field_info.get("options", {})
                        actual_option_name = self._find_case_insensitive_key(
                            options, filter_field_value
                        )
                        if actual_option_name:
                            option_id = options.get(actual_option_name)
                            logger.info(
                                f"Found option '{actual_option_name}' using case-insensitive match for '{filter_field_value}'"
                            )

                    if not option_id:
                        raise ValueError(
                            f"Option '{filter_field_value}' not found for field '{filter_field_name}'. Available: {available_options}"
                        )
                    field_id_var = field_id
                    option_id_var = option_id
                    logger.debug(
                        f"Using field ID {field_id_var} with option ID {option_id_var} for filtering"
                    )
                elif field_type == "ProjectV2IterationField":
                    available_iterations = list(field_info.get("iterations", {}).keys())
                    logger.debug(
                        f"Available iterations for '{filter_field_name}': {available_iterations}"
                    )

                    # First try exact match
                    iteration_id = field_info.get("iterations", {}).get(
                        filter_field_value
                    )
                    # If not found, try case-insensitive match
                    if not iteration_id:
                        iterations = field_info.get("iterations", {})
                        actual_iteration_name = self._find_case_insensitive_key(
                            iterations, filter_field_value
                        )
                        if actual_iteration_name:
                            iteration_id = iterations.get(actual_iteration_name)
                            logger.info(
                                f"Found iteration '{actual_iteration_name}' using case-insensitive match for '{filter_field_value}'"
                            )

                    if not iteration_id:
                        raise ValueError(
                            f"Iteration '{filter_field_value}' not found for field '{filter_field_name}'. Available: {available_iterations}"
                        )
                    field_id_var = field_id
                    option_id_var = iteration_id
                    logger.debug(
                        f"Using field ID {field_id_var} with iteration ID {option_id_var} for filtering"
                    )
                else:
                    logger.warning(
                        f"Filtering by field type '{field_type}' is not yet implemented."
                    )
            except GitHubClientError as e:
                logger.error(f"Error during field lookup for filtering: {e}")
                raise
            except ValueError as e:
                logger.error(f"Invalid filter input: {e}")
                raise

        # Use single curly braces for GraphQL, not double curly braces for f-string
        query = f"""
        {field_values_fragment}
        {content_fragment}
        query GetProjectItems($projectId: ID!, $first: Int!{', $cursor: String' if cursor else ''}) {{
          node(id: $projectId) {{
            ... on ProjectV2 {{
              items(first: $first{after_clause}) {{
                pageInfo {{
                  hasNextPage
                  endCursor
                }}
                nodes {{
                  id
                  type
                  fieldValues(first: 20) {{ ...FieldValuesFragment }}
                  content {{ ...ContentFragment }}
                }}
              }}
            }}
          }}
        }}
        """

        logger.debug(f"Executing items query: {query} with vars: {variables}")

        try:
            result = await self.execute_query(query, variables)
            if result is None:
                logger.warning(
                    f"Query returned None result for project {owner}/{project_number}"
                )
                return {
                    "items": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }

            items_data = result.get("node", {}).get("items")
            if items_data is None:  # Check if items key exists, even if null
                if result.get("node") is None:
                    raise GitHubClientError(
                        f"Project node not found for {owner}/{project_number}"
                    )
                else:
                    logger.info(
                        f"No items found matching filter criteria for project {owner}/{project_number}"
                    )
                    return {
                        "items": [],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }

            # Get pagination info
            page_info = items_data.get("pageInfo", {})
            items = items_data.get("nodes", [])

            logger.debug(
                f"Retrieved {len(items)} items from project {owner}/{project_number}"
            )

            # Process field values
            filtered_items = []
            for item in items:
                if item.get("fieldValues") and item["fieldValues"].get("nodes"):
                    field_values = item["fieldValues"]["nodes"]

                    processed_values = {}
                    matches_field_filter = (
                        False if (field_id_var and option_id_var) else True
                    )

                    for fv in field_values:
                        raw_field_name = fv.get("field", {}).get("name")
                        # Sanitize the field name
                        if raw_field_name:
                            # Remove chars other than alphanumeric, space, underscore, hyphen
                            sanitized_field_name = re.sub(
                                r"[^\w\s-]", "", raw_field_name
                            ).strip()
                        else:
                            sanitized_field_name = "UnknownField"

                        field_name = (
                            sanitized_field_name or "UnnamedField"
                        )  # Ensure not empty

                        value = "N/A"
                        fv_type = fv.get("__typename")
                        if fv_type == "ProjectV2ItemFieldTextValue":
                            value = fv.get("text", "N/A")
                        elif fv_type == "ProjectV2ItemFieldDateValue":
                            value = fv.get("date", "N/A")
                        elif fv_type == "ProjectV2ItemFieldSingleSelectValue":
                            value = fv.get("name", "N/A")
                            # Check if this is the field we're filtering on
                            if (
                                field_id_var
                                and option_id_var
                                and field_name
                                and filter_field_name
                                and field_name.lower() == filter_field_name.lower()
                                and value
                                and filter_field_value
                                and value.lower() == filter_field_value.lower()
                            ):
                                matches_field_filter = True
                                logger.debug(
                                    f"Found matching item with field '{field_name}' = '{value}'"
                                )
                            elif (
                                field_id_var
                                and option_id_var
                                and field_name
                                and filter_field_name
                                and field_name.lower() == filter_field_name.lower()
                            ):
                                logger.debug(
                                    f"Field name matched but value did not: '{value}' != '{filter_field_value}'"
                                )
                        elif fv_type == "ProjectV2ItemFieldNumberValue":
                            value = fv.get("number", "N/A")
                        elif fv_type == "ProjectV2ItemFieldIterationValue":
                            title = fv.get("title", "N/A")
                            value = f"{title} (Start: {fv.get('startDate', 'N/A')})"
                            # Check if this is the field we're filtering on
                            if (
                                field_id_var
                                and option_id_var
                                and field_name
                                and filter_field_name
                                and field_name.lower() == filter_field_name.lower()
                                and title
                                and filter_field_value
                                and title.lower() == filter_field_value.lower()
                            ):
                                matches_field_filter = True
                                logger.debug(
                                    f"Found matching item with iteration field '{field_name}' = '{title}'"
                                )
                        processed_values[field_name] = value

                    item["fieldValues"] = processed_values

                    # Apply state filter if needed
                    matches_state_filter = True
                    if state and item.get("content"):
                        content_state = item["content"].get("state")
                        if content_state and content_state != state.upper():
                            matches_state_filter = False

                    if matches_field_filter and matches_state_filter:
                        filtered_items.append(item)
                else:
                    # Items without field values are included only if we're not doing field filtering
                    if not (field_id_var and option_id_var):
                        filtered_items.append(item)

            # When filtering, we may have fetched more than requested, so trim to the requested limit
            if filter_field_name and filter_field_value and len(filtered_items) > limit:
                filtered_items = filtered_items[:limit]
                # Update pagination info to indicate there may be more filtered results
                page_info = {
                    "hasNextPage": True,
                    "endCursor": page_info.get("endCursor"),
                }

            # Emergency check: if we're filtering and got very few results, warn that there might be more
            if (
                filter_field_name
                and filter_field_value
                and len(filtered_items) == 0
                and len(items) >= fetch_limit
                and fetch_limit < 100
            ):
                logger.warning(
                    f"Found 0 filtered items but fetched the maximum ({fetch_limit}). There might be more items beyond this limit. Consider increasing the search scope."
                )

            logger.debug(
                f"Filtered down to {len(filtered_items)} items for project {owner}/{project_number} using criteria field_name={filter_field_name}, field_value={filter_field_value}"
            )
            return {"items": filtered_items, "pageInfo": page_info}
        except GitHubClientError as e:
            logger.error(
                f"Failed to get items for project {owner}/{project_number}: {e}"
            )
            raise

    async def create_issue(
        self, owner: str, repo: str, title: str, body: str = ""
    ) -> Dict[str, Any]:
        """Create a new GitHub issue.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            title: The issue title
            body: The issue body (optional)

        Returns:
            The created issue data

        Raises:
            GitHubClientError: If repository is not found or issue creation fails.
        """
        query = """
        mutation CreateIssue($repositoryId: ID!, $title: String!, $body: String) {
          createIssue(input: {
            repositoryId: $repositoryId,
            title: $title,
            body: $body
          }) {
            issue {
              id
              number
              title
              url
              state
            }
          }
        }
        """

        # First get the repository ID
        repo_query = """
        query GetRepositoryId($owner: String!, $name: String!) {
          repository(owner: $owner, name: $name) {
            id
          }
        }
        """

        repo_variables = {"owner": owner, "name": repo}

        try:
            repo_result = await self.execute_query(repo_query, repo_variables)
            if not repo_result.get("repository"):
                raise GitHubClientError(f"Repository {owner}/{repo} not found")
        except GitHubClientError as e:
            logger.error(f"Failed to get repository ID for {owner}/{repo}: {e}")
            raise

        repository_id = repo_result["repository"]["id"]

        variables = {"repositoryId": repository_id, "title": title, "body": body}

        try:
            result = await self.execute_query(query, variables)
            if not result.get("createIssue") or not result["createIssue"].get("issue"):
                raise GitHubClientError(f"Failed to create issue in {owner}/{repo}")
            return result["createIssue"]["issue"]
        except GitHubClientError as e:
            logger.error(f"Failed to create issue in {owner}/{repo}: {e}")
            raise

    async def add_issue_to_project(
        self,
        owner: str,
        project_number: int,
        issue_owner: str,
        issue_repo: str,
        issue_number: int,
    ) -> Dict[str, Any]:
        """Add an existing GitHub issue to a Project V2.

        Args:
            owner: The GitHub organization or user name that owns the project
            project_number: The project number
            issue_owner: The owner of the repository containing the issue
            issue_repo: The repository name containing the issue
            issue_number: The issue number

        Returns:
            The project item data

        Raises:
            GitHubClientError: If project or issue is not found, or adding fails.
        """
        # Get project ID
        try:
            project_id = await self.get_project_node_id(owner, project_number)
        except GitHubClientError as e:
            logger.error(f"Cannot add issue: {e}")
            raise

        # Get issue ID
        issue_query = """
        query GetIssueId($owner: String!, $repo: String!, $number: Int!) {
          repository(owner: $owner, name: $repo) {
            issue(number: $number) {
              id
            }
          }
        }
        """

        issue_variables = {
            "owner": issue_owner,
            "repo": issue_repo,
            "number": issue_number,
        }

        try:
            issue_result = await self.execute_query(issue_query, issue_variables)
            if not issue_result.get("repository") or not issue_result["repository"].get(
                "issue"
            ):
                raise GitHubClientError(
                    f"Issue {issue_number} not found in {issue_owner}/{issue_repo}"
                )
        except GitHubClientError as e:
            logger.error(
                f"Failed to get issue ID for {issue_owner}/{issue_repo}#{issue_number}: {e}"
            )
            raise

        issue_id = issue_result["repository"]["issue"]["id"]

        # Add issue to project
        add_query = """
        mutation AddItemToProject($projectId: ID!, $contentId: ID!) {
          addProjectV2ItemById(input: {
            projectId: $projectId,
            contentId: $contentId
          }) {
            item {
              id
              content {
                ... on Issue {
                  title
                  number
                }
                ... on PullRequest {
                  title
                  number
                }
              }
            }
          }
        }
        """

        variables = {"projectId": project_id, "contentId": issue_id}

        try:
            result = await self.execute_query(add_query, variables)
            if not result.get("addProjectV2ItemById") or not result[
                "addProjectV2ItemById"
            ].get("item"):
                raise GitHubClientError(
                    f"Failed to add issue {issue_number} to project {project_number}"
                )
            return result["addProjectV2ItemById"]["item"]
        except GitHubClientError as e:
            logger.error(
                f"Failed to add issue {issue_number} to project {project_number}: {e}"
            )
            raise

    async def add_draft_issue_to_project(
        self, owner: str, project_number: int, title: str, body: str = ""
    ) -> Dict[str, Any]:
        """Add a draft issue to a GitHub Project V2.

        Args:
            owner: The GitHub organization or user name that owns the project
            project_number: The project number
            title: The draft issue title
            body: The draft issue body (optional)

        Returns:
            The project item data

        Raises:
            GitHubClientError: If project not found or adding fails.
        """
        # Get project ID
        try:
            project_id = await self.get_project_node_id(owner, project_number)
        except GitHubClientError as e:
            logger.error(f"Cannot add draft issue: {e}")
            raise

        # Add draft issue to project
        add_query = """
        mutation AddDraftIssueToProject($projectId: ID!, $title: String!, $body: String) {
          addProjectV2DraftIssue(input: {
            projectId: $projectId,
            title: $title,
            body: $body
          }) {
            projectItem {
              id
            }
          }
        }
        """

        variables = {"projectId": project_id, "title": title, "body": body}

        try:
            result = await self.execute_query(add_query, variables)
            if not result.get("addProjectV2DraftIssue") or not result[
                "addProjectV2DraftIssue"
            ].get("projectItem"):
                raise GitHubClientError(
                    f"Failed to add draft issue to project {project_number}"
                )
            return result["addProjectV2DraftIssue"]["projectItem"]
        except GitHubClientError as e:
            logger.error(f"Failed to add draft issue to project {project_number}: {e}")
            raise

    async def update_project_item_field(
        self,
        owner: str,
        project_number: int,
        item_id: str,
        field_id: str,
        value: Any,  # Value type depends on the field
    ) -> Dict[str, Any]:
        """Update a field value for an item in a GitHub Project V2.

        Args:
            owner: The GitHub organization or user name that owns the project
            project_number: The project number
            item_id: The project item ID
            field_id: The field ID to update
            value: The new value (type depends on field: string, number, date, boolean, iteration ID, single select option ID)

        Returns:
            The updated project item data (containing the item ID)

        Raises:
            GitHubClientError: If project not found or update fails.
        """
        # Get project ID
        try:
            project_id = await self.get_project_node_id(owner, project_number)
        except GitHubClientError as e:
            logger.error(f"Cannot update item field: {e}")
            raise

        # Get field details to determine the correct field type
        try:
            field_details = await self.get_project_fields_details(owner, project_number)
        except GitHubClientError as e:
            logger.error(f"Cannot get field details for field type detection: {e}")
            raise

        # Find the field by ID
        target_field = None
        for field_name, details in field_details.items():
            if details.get("id") == field_id:
                target_field = details
                break

        if not target_field:
            raise GitHubClientError(f"Field with ID {field_id} not found in project")

        field_type = target_field.get("type")
        data_type = target_field.get("dataType")
        
        logger.debug(f"Field ID: {field_id}, Type: {field_type}, DataType: {data_type}")

        # Prepare value based on actual field type and dataType
        field_value_input: Dict[str, Any] = {}

        if field_type == "ProjectV2SingleSelectField":
            if isinstance(value, str):
                field_value_input = {"singleSelectOptionId": value}
            else:
                raise GitHubClientError(
                    f"Invalid value type for single select field {field_id}. Expected option ID string."
                )
        elif field_type == "ProjectV2IterationField":
            if isinstance(value, str):
                field_value_input = {"iterationId": value}
            else:
                raise GitHubClientError(
                    f"Invalid value type for iteration field {field_id}. Expected iteration ID string."
                )
        elif field_type == "ProjectV2Field":
            # For ProjectV2Field, use dataType to determine the correct value format
            if data_type == "TEXT":
                field_value_input = {"text": str(value)}
            elif data_type == "NUMBER":
                try:
                    # Convert string numbers to float for GraphQL
                    if isinstance(value, str):
                        field_value_input = {"number": float(value)}
                    elif isinstance(value, (int, float)):
                        field_value_input = {"number": float(value)}
                    else:
                        raise ValueError(f"Cannot convert {value} to number")
                except (ValueError, TypeError) as e:
                    raise GitHubClientError(
                        f"Invalid value for number field {field_id}: {value}. Error: {e}"
                    )
            elif data_type == "DATE":
                if isinstance(value, str):
                    field_value_input = {"date": value}
                else:
                    raise GitHubClientError(
                        f"Invalid value type for date field {field_id}. Expected date string (YYYY-MM-DD)."
                    )
            else:
                # Unknown dataType, default to text
                logger.warning(
                    f"Unknown dataType '{data_type}' for ProjectV2Field {field_id}. Defaulting to text."
                )
                field_value_input = {"text": str(value)}
        else:
            # Unknown field type, default to text
            logger.warning(
                f"Unknown field type '{field_type}' for {field_id}. Defaulting to text."
            )
            field_value_input = {"text": str(value)}

        # Update field value
        update_query = """
        mutation UpdateProjectFieldValue($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: ProjectV2FieldValue!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId,
            itemId: $itemId,
            fieldId: $fieldId,
            value: $value
          }) {
            projectV2Item {
              id
            }
          }
        }
        """

        variables = {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": field_id,
            "value": field_value_input,
        }

        try:
            result = await self.execute_query(update_query, variables)
            if not result.get("updateProjectV2ItemFieldValue") or not result[
                "updateProjectV2ItemFieldValue"
            ].get("projectV2Item"):
                raise GitHubClientError(
                    f"Failed to update field value for item {item_id}"
                )
            return result["updateProjectV2ItemFieldValue"]["projectV2Item"]
        except GitHubClientError as e:
            logger.error(f"Failed to update field {field_id} for item {item_id}: {e}")
            raise

    async def delete_project_item(
        self, owner: str, project_number: int, item_id: str
    ) -> str:
        """Delete an item from a GitHub Project V2.

        Args:
            owner: The GitHub organization or user name that owns the project
            project_number: The project number
            item_id: The project item ID

        Returns:
            The ID of the deleted item.

        Raises:
            GitHubClientError: If project not found or deletion fails.
        """
        # Get project ID
        try:
            project_id = await self.get_project_node_id(owner, project_number)
        except GitHubClientError as e:
            logger.error(f"Cannot delete item: {e}")
            raise

        # Delete item
        delete_query = """
        mutation DeleteProjectItem($projectId: ID!, $itemId: ID!) {
          deleteProjectV2Item(input: {
            projectId: $projectId,
            itemId: $itemId
          }) {
            deletedItemId
          }
        }
        """

        variables = {"projectId": project_id, "itemId": item_id}

        try:
            result = await self.execute_query(delete_query, variables)
            if not result.get("deleteProjectV2Item") or not result[
                "deleteProjectV2Item"
            ].get("deletedItemId"):
                raise GitHubClientError(f"Failed to delete item {item_id}")
            return result["deleteProjectV2Item"]["deletedItemId"]
        except GitHubClientError as e:
            logger.error(f"Failed to delete item {item_id}: {e}")
            raise

    async def update_project_settings(
        self,
        owner: str,
        project_number: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        public: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update GitHub Project V2 settings.

        Args:
            owner: The GitHub organization or user name that owns the project
            project_number: The project number
            title: New project title (optional)
            description: New project description (optional)
            public: Whether the project should be public (optional)

        Returns:
            The updated project data

        Raises:
            GitHubClientError: If project not found or update fails.
        """
        # Get project ID
        try:
            project_id = await self.get_project_node_id(owner, project_number)
        except GitHubClientError as e:
            logger.error(f"Cannot update project settings: {e}")
            raise

        # Build input parameters
        input_params: Dict[str, Any] = {"projectId": project_id}  # Use Dict[str, Any]

        if title is not None:
            input_params["title"] = title

        if description is not None:
            input_params["shortDescription"] = description

        if public is not None:
            input_params["public"] = public  # Keep as boolean

        # Update project
        update_query = """
        mutation UpdateProject($input: UpdateProjectV2Input!) {
          updateProjectV2(input: $input) {
            projectV2 {
              id
              title
              shortDescription
              public
              url
            }
          }
        }
        """

        variables = {"input": input_params}

        try:
            result = await self.execute_query(update_query, variables)
            if not result.get("updateProjectV2") or not result["updateProjectV2"].get(
                "projectV2"
            ):
                raise GitHubClientError(f"Failed to update project {project_number}")
            return result["updateProjectV2"]["projectV2"]
        except GitHubClientError as e:
            logger.error(f"Failed to update project {project_number}: {e}")
            raise

    async def list_repository_milestones(
        self,
        owner: str,
        repo: str,
        state: Optional[str] = None,
        sort: Optional[str] = None,
        direction: Optional[str] = None,
        per_page: int = 30,
        page: int = 1,
    ) -> List[Dict[str, Any]]:
        """List milestones for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            state: The state of milestones to return ('open', 'closed', 'all')
            sort: What to sort results by ('due_on', 'completeness')
            direction: The direction of the sort ('asc', 'desc')
            per_page: Results per page (max 100)
            page: Page number of results to fetch

        Returns:
            List of milestone dictionaries

        Raises:
            GitHubClientError: If the repository is not found or milestones cannot be retrieved.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/milestones"
        
        # Build query parameters
        params = {}
        if state:
            params["state"] = state
        if sort:
            params["sort"] = sort
        if direction:
            params["direction"] = direction
        if per_page != 30:
            params["per_page"] = per_page
        if page != 1:
            params["page"] = page

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                milestones = response.json()
                
                if not isinstance(milestones, list):
                    raise GitHubClientError(f"Unexpected response format from GitHub API")
                    
                return milestones
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error listing milestones for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error listing milestones for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def create_milestone(
        self,
        owner: str,
        repo: str,
        title: str,
        description: Optional[str] = None,
        due_on: Optional[str] = None,
        state: str = "open",
    ) -> Dict[str, Any]:
        """Create a milestone for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            title: The title of the milestone
            description: A description of the milestone
            due_on: The milestone due date in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)
            state: The state of the milestone ('open' or 'closed')

        Returns:
            The created milestone dictionary

        Raises:
            GitHubClientError: If the repository is not found or milestone cannot be created.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/milestones"
        
        # Build request body
        body = {"title": title, "state": state}
        if description:
            body["description"] = description
        if due_on:
            body["due_on"] = due_on

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "Content-Type": "application/json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    json=body,
                    timeout=30.0,
                )
                response.raise_for_status()
                milestone = response.json()
                
                if not isinstance(milestone, dict):
                    raise GitHubClientError(f"Unexpected response format from GitHub API")
                    
                return milestone
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error creating milestone for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error creating milestone for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def get_milestone(
        self,
        owner: str,
        repo: str,
        milestone_number: int,
    ) -> Dict[str, Any]:
        """Get a specific milestone for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            milestone_number: The number of the milestone

        Returns:
            The milestone dictionary

        Raises:
            GitHubClientError: If the repository or milestone is not found.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/milestones/{milestone_number}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                milestone = response.json()
                
                if not isinstance(milestone, dict):
                    raise GitHubClientError(f"Unexpected response format from GitHub API")
                    
                return milestone
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error getting milestone {milestone_number} for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error getting milestone {milestone_number} for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def update_milestone(
        self,
        owner: str,
        repo: str,
        milestone_number: int,
        title: Optional[str] = None,
        state: Optional[str] = None,
        description: Optional[str] = None,
        due_on: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a milestone for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            milestone_number: The number of the milestone
            title: The title of the milestone
            state: The state of the milestone ('open' or 'closed')
            description: A description of the milestone
            due_on: The milestone due date in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)

        Returns:
            The updated milestone dictionary

        Raises:
            GitHubClientError: If the repository or milestone is not found.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/milestones/{milestone_number}"
        
        # Build request body with only provided fields
        body = {}
        if title is not None:
            body["title"] = title
        if state is not None:
            body["state"] = state
        if description is not None:
            body["description"] = description
        if due_on is not None:
            body["due_on"] = due_on

        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "Content-Type": "application/json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    json=body,
                    timeout=30.0,
                )
                response.raise_for_status()
                milestone = response.json()
                
                if not isinstance(milestone, dict):
                    raise GitHubClientError(f"Unexpected response format from GitHub API")
                    
                return milestone
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error updating milestone {milestone_number} for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error updating milestone {milestone_number} for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def delete_milestone(
        self,
        owner: str,
        repo: str,
        milestone_number: int,
    ) -> bool:
        """Delete a milestone for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            milestone_number: The number of the milestone

        Returns:
            True if deletion was successful

        Raises:
            GitHubClientError: If the repository or milestone is not found.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/milestones/{milestone_number}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                return True
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error deleting milestone {milestone_number} for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error deleting milestone {milestone_number} for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def delete_issue(
        self, owner: str, repo: str, issue_number: int
    ) -> bool:
        """Delete an issue from a GitHub repository using GitHub GraphQL API.

        IMPORTANT: This operation is permanent and cannot be undone. Requires admin
        permissions on the repository. Organization owners must have enabled issue
        deletion for the organization.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            issue_number: The issue number to delete

        Returns:
            True if deletion was successful

        Raises:
            GitHubClientError: If repository or issue is not found, insufficient permissions,
                             or organization doesn't allow issue deletion.
        """
        # First get the issue node ID
        issue_query = """
        query GetIssueId($owner: String!, $repo: String!, $number: Int!) {
          repository(owner: $owner, name: $repo) {
            issue(number: $number) {
              id
            }
          }
        }
        """

        issue_variables = {
            "owner": owner,
            "repo": repo,
            "number": issue_number,
        }

        try:
            issue_result = await self.execute_query(issue_query, issue_variables)
            if not issue_result.get("repository"):
                raise GitHubClientError(f"Repository {owner}/{repo} not found")
            if not issue_result["repository"].get("issue"):
                raise GitHubClientError(
                    f"Issue #{issue_number} not found in {owner}/{repo}"
                )
        except GitHubClientError as e:
            logger.error(
                f"Failed to get issue ID for {owner}/{repo}#{issue_number}: {e}"
            )
            raise

        issue_id = issue_result["repository"]["issue"]["id"]

        # Delete the issue using GraphQL mutation
        delete_query = """
        mutation DeleteIssue($issueId: ID!) {
          deleteIssue(input: {
            issueId: $issueId
          }) {
            repository {
              id
            }
          }
        }
        """

        variables = {"issueId": issue_id}

        try:
            result = await self.execute_query(delete_query, variables)
            if not result.get("deleteIssue"):
                raise GitHubClientError(
                    f"Failed to delete issue #{issue_number} from {owner}/{repo}"
                )
            return True
        except GitHubClientError as e:
            # Check for specific error patterns and provide better error messages
            error_msg = str(e).lower()
            if "insufficient" in error_msg or "permission" in error_msg or "forbidden" in error_msg:
                raise GitHubClientError(
                    f"Insufficient permissions to delete issue #{issue_number} from {owner}/{repo}. Admin permissions required."
                ) from e
            elif "not found" in error_msg:
                raise GitHubClientError(
                    f"Issue #{issue_number} not found in {owner}/{repo}"
                ) from e
            else:
                logger.error(f"Failed to delete issue #{issue_number} from {owner}/{repo}: {e}")
                raise GitHubClientError(
                    f"Failed to delete issue #{issue_number} from {owner}/{repo}: {e}"
                ) from e

    # --- Repository Secrets Management ---

    async def list_repository_actions_secrets(
        self,
        owner: str,
        repo: str,
        per_page: int = 30,
        page: int = 1,
    ) -> Dict[str, Any]:
        """List Actions secrets for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            per_page: Results per page (max 100)
            page: Page number of results to fetch

        Returns:
            Dictionary containing total_count and secrets array

        Raises:
            GitHubClientError: If the repository is not found or secrets cannot be retrieved.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets"
        
        # Build query parameters
        params = {}
        if per_page != 30:
            params["per_page"] = per_page
        if page != 1:
            params["page"] = page

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                secrets = response.json()
                
                if not isinstance(secrets, dict):
                    raise GitHubClientError(f"Unexpected response format from GitHub API")
                    
                return secrets
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error listing Actions secrets for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error listing Actions secrets for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def get_repository_actions_secret(
        self,
        owner: str,
        repo: str,
        secret_name: str,
    ) -> Dict[str, Any]:
        """Get a specific Actions secret for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            secret_name: The name of the secret

        Returns:
            The secret dictionary

        Raises:
            GitHubClientError: If the repository or secret is not found.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/{secret_name}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                secret = response.json()
                
                if not isinstance(secret, dict):
                    raise GitHubClientError(f"Unexpected response format from GitHub API")
                    
                return secret
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error getting Actions secret {secret_name} for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error getting Actions secret {secret_name} for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def get_repository_actions_public_key(
        self,
        owner: str,
        repo: str,
    ) -> Dict[str, Any]:
        """Get the Actions public key for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name

        Returns:
            The public key dictionary with key_id and key

        Raises:
            GitHubClientError: If the repository is not found.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/public-key"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                public_key = response.json()
                
                if not isinstance(public_key, dict):
                    raise GitHubClientError(f"Unexpected response format from GitHub API")
                    
                return public_key
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error getting Actions public key for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error getting Actions public key for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def create_or_update_repository_actions_secret(
        self,
        owner: str,
        repo: str,
        secret_name: str,
        secret_value: str,
        key_id: str,
    ) -> bool:
        """Create or update an Actions secret for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            secret_name: The name of the secret
            secret_value: The plaintext secret value (will be encrypted)
            key_id: The ID of the public key used for encryption

        Returns:
            True if successful

        Raises:
            GitHubClientError: If the repository is not found or secret cannot be created.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/{secret_name}"
        
        # Get public key to encrypt the secret
        try:
            public_key_data = await self.get_repository_actions_public_key(owner, repo)
            public_key = public_key_data["key"]
            
            # Encrypt the secret value
            encrypted_value = self.encrypt_secret_value(secret_value, public_key)
            
        except Exception as e:
            error_message = f"Failed to encrypt secret value: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        
        # Build request body
        body = {
            "encrypted_value": encrypted_value,
            "key_id": key_id
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "Content-Type": "application/json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    json=body,
                    timeout=30.0,
                )
                response.raise_for_status()
                return True
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error creating/updating Actions secret {secret_name} for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error creating/updating Actions secret {secret_name} for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def delete_repository_actions_secret(
        self,
        owner: str,
        repo: str,
        secret_name: str,
    ) -> bool:
        """Delete an Actions secret for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            secret_name: The name of the secret

        Returns:
            True if deletion was successful

        Raises:
            GitHubClientError: If the repository or secret is not found.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/{secret_name}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                return True
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error deleting Actions secret {secret_name} for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error deleting Actions secret {secret_name} for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    # --- Codespaces Secrets Management ---

    async def list_repository_codespaces_secrets(
        self,
        owner: str,
        repo: str,
        per_page: int = 30,
        page: int = 1,
    ) -> Dict[str, Any]:
        """List Codespaces secrets for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            per_page: Results per page (max 100)
            page: Page number of results to fetch

        Returns:
            Dictionary containing total_count and secrets array

        Raises:
            GitHubClientError: If the repository is not found or secrets cannot be retrieved.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/codespaces/secrets"
        
        # Build query parameters
        params = {}
        if per_page != 30:
            params["per_page"] = per_page
        if page != 1:
            params["page"] = page

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                secrets = response.json()
                
                if not isinstance(secrets, dict):
                    raise GitHubClientError(f"Unexpected response format from GitHub API")
                    
                return secrets
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error listing Codespaces secrets for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error listing Codespaces secrets for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def get_repository_codespaces_secret(
        self,
        owner: str,
        repo: str,
        secret_name: str,
    ) -> Dict[str, Any]:
        """Get a specific Codespaces secret for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            secret_name: The name of the secret

        Returns:
            The secret dictionary

        Raises:
            GitHubClientError: If the repository or secret is not found.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/codespaces/secrets/{secret_name}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                secret = response.json()
                
                if not isinstance(secret, dict):
                    raise GitHubClientError(f"Unexpected response format from GitHub API")
                    
                return secret
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error getting Codespaces secret {secret_name} for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error getting Codespaces secret {secret_name} for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def get_repository_codespaces_public_key(
        self,
        owner: str,
        repo: str,
    ) -> Dict[str, Any]:
        """Get the Codespaces public key for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name

        Returns:
            The public key dictionary with key_id and key

        Raises:
            GitHubClientError: If the repository is not found.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/codespaces/secrets/public-key"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                public_key = response.json()
                
                if not isinstance(public_key, dict):
                    raise GitHubClientError(f"Unexpected response format from GitHub API")
                    
                return public_key
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error getting Codespaces public key for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error getting Codespaces public key for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def create_or_update_repository_codespaces_secret(
        self,
        owner: str,
        repo: str,
        secret_name: str,
        secret_value: str,
        key_id: str,
    ) -> bool:
        """Create or update a Codespaces secret for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            secret_name: The name of the secret
            secret_value: The plaintext secret value (will be encrypted)
            key_id: The ID of the public key used for encryption

        Returns:
            True if successful

        Raises:
            GitHubClientError: If the repository is not found or secret cannot be created.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/codespaces/secrets/{secret_name}"
        
        # Get public key to encrypt the secret
        try:
            public_key_data = await self.get_repository_codespaces_public_key(owner, repo)
            public_key = public_key_data["key"]
            
            # Encrypt the secret value
            encrypted_value = self.encrypt_secret_value(secret_value, public_key)
            
        except Exception as e:
            error_message = f"Failed to encrypt secret value: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        
        # Build request body
        body = {
            "encrypted_value": encrypted_value,
            "key_id": key_id
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "Content-Type": "application/json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    json=body,
                    timeout=30.0,
                )
                response.raise_for_status()
                return True
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error creating/updating Codespaces secret {secret_name} for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error creating/updating Codespaces secret {secret_name} for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def delete_repository_codespaces_secret(
        self,
        owner: str,
        repo: str,
        secret_name: str,
    ) -> bool:
        """Delete a Codespaces secret for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            secret_name: The name of the secret

        Returns:
            True if deletion was successful

        Raises:
            GitHubClientError: If the repository or secret is not found.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/codespaces/secrets/{secret_name}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                return True
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error deleting Codespaces secret {secret_name} for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error deleting Codespaces secret {secret_name} for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    # --- Dependabot Secrets Management ---

    async def list_repository_dependabot_secrets(
        self,
        owner: str,
        repo: str,
        per_page: int = 30,
        page: int = 1,
    ) -> Dict[str, Any]:
        """List Dependabot secrets for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            per_page: Results per page (max 100)
            page: Page number of results to fetch

        Returns:
            Dictionary containing total_count and secrets array

        Raises:
            GitHubClientError: If the repository is not found or secrets cannot be retrieved.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/dependabot/secrets"
        
        # Build query parameters
        params = {}
        if per_page != 30:
            params["per_page"] = per_page
        if page != 1:
            params["page"] = page

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                secrets = response.json()
                
                if not isinstance(secrets, dict):
                    raise GitHubClientError(f"Unexpected response format from GitHub API")
                    
                return secrets
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error listing Dependabot secrets for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error listing Dependabot secrets for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def get_repository_dependabot_secret(
        self,
        owner: str,
        repo: str,
        secret_name: str,
    ) -> Dict[str, Any]:
        """Get a specific Dependabot secret for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            secret_name: The name of the secret

        Returns:
            The secret dictionary

        Raises:
            GitHubClientError: If the repository or secret is not found.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/dependabot/secrets/{secret_name}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                secret = response.json()
                
                if not isinstance(secret, dict):
                    raise GitHubClientError(f"Unexpected response format from GitHub API")
                    
                return secret
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error getting Dependabot secret {secret_name} for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error getting Dependabot secret {secret_name} for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def get_repository_dependabot_public_key(
        self,
        owner: str,
        repo: str,
    ) -> Dict[str, Any]:
        """Get the Dependabot public key for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name

        Returns:
            The public key dictionary with key_id and key

        Raises:
            GitHubClientError: If the repository is not found.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/dependabot/secrets/public-key"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                public_key = response.json()
                
                if not isinstance(public_key, dict):
                    raise GitHubClientError(f"Unexpected response format from GitHub API")
                    
                return public_key
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error getting Dependabot public key for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error getting Dependabot public key for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def create_or_update_repository_dependabot_secret(
        self,
        owner: str,
        repo: str,
        secret_name: str,
        secret_value: str,
        key_id: str,
    ) -> bool:
        """Create or update a Dependabot secret for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            secret_name: The name of the secret
            secret_value: The plaintext secret value (will be encrypted)
            key_id: The ID of the public key used for encryption

        Returns:
            True if successful

        Raises:
            GitHubClientError: If the repository is not found or secret cannot be created.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/dependabot/secrets/{secret_name}"
        
        # Get public key to encrypt the secret
        try:
            public_key_data = await self.get_repository_dependabot_public_key(owner, repo)
            public_key = public_key_data["key"]
            
            # Encrypt the secret value
            encrypted_value = self.encrypt_secret_value(secret_value, public_key)
            
        except Exception as e:
            error_message = f"Failed to encrypt secret value: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        
        # Build request body
        body = {
            "encrypted_value": encrypted_value,
            "key_id": key_id
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "Content-Type": "application/json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    json=body,
                    timeout=30.0,
                )
                response.raise_for_status()
                return True
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error creating/updating Dependabot secret {secret_name} for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error creating/updating Dependabot secret {secret_name} for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e

    async def delete_repository_dependabot_secret(
        self,
        owner: str,
        repo: str,
        secret_name: str,
    ) -> bool:
        """Delete a Dependabot secret for a repository using GitHub REST API.

        Args:
            owner: The GitHub organization or user name
            repo: The repository name
            secret_name: The name of the secret

        Returns:
            True if deletion was successful

        Raises:
            GitHubClientError: If the repository or secret is not found.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/dependabot/secrets/{secret_name}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                return True
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error deleting Dependabot secret {secret_name} for {owner}/{repo}: {e.response.status_code} - {e.response.text}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
        except Exception as e:
            error_message = f"Unexpected error deleting Dependabot secret {secret_name} for {owner}/{repo}: {str(e)}"
            logger.error(error_message)
            raise GitHubClientError(error_message) from e
