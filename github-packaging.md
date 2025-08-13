<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Publishing Your Python MCP Package: GitHub-Only Distribution Guide

Based on your fork of the `github-projects-mcp` repository, I understand you want to enable the same `uvx mcp-package-name` installation pattern as the original while keeping your package published only on GitHub (not PyPI). Here's a comprehensive guide to accomplish this.

## The Reality Check

The simple `uvx mcp-github-projects` command works for the original package because it's published on PyPI. For GitHub-only publishing, you cannot achieve the exact same simplicity due to how `uvx` resolves packages. However, I'll show you the best alternatives that come very close.[^1][^2]

![Comparison of Python Package Publishing Options for MCP Server](https://ppl-ai-code-interpreter-files.s3.amazonaws.com/web/direct-files/f3d21837f8f3195bf835d59c4f883afa/d3899dbe-0b91-4a1e-8c5e-9e8b76a8aa34/404f4a0d.png)

Comparison of Python Package Publishing Options for MCP Server

## Recommended Solution: Direct Git Installation

The most practical approach for your use case is **Direct Git Installation**. Here's how to implement it:

### 1. Package Structure Setup

Ensure your fork has the proper structure in your `pyproject.toml`:

### 2. Installation Command

Users will install your package with:

```bash
uvx --from git+https://github.com/mweichert/github-projects-mcp@add-milestone-tools mcp-github-projects-mweichert
```


### 3. Claude Desktop Configuration

### 4. User-Friendly Installation Scripts

To make installation easier for users, add these scripts to your repository:

**For Unix/Linux/macOS (`install.sh`):**

**For Windows (`install.ps1`):**

Users can then install with a single command:

```bash
curl -fsSL https://raw.githubusercontent.com/mweichert/github-projects-mcp/add-milestone-tools/install.sh | bash
```


## Alternative: GitHub Releases with Automation

For a more polished experience, you can set up automated releases with this GitHub Actions workflow:

This workflow will:

- Build packages automatically when you create version tags
- Attach distributions to GitHub releases
- Generate release notes with installation instructions
- Test the package installation


## Why Simple `uvx package-name` Won't Work

The key limitation is that `uvx` without the `--from` flag only searches PyPI and other configured package indices. GitHub Package Registry for Python:

1. **Doesn't integrate seamlessly** with `uvx` like PyPI does[^3][^4]
2. **Requires authentication** for most operations[^5][^6]
3. **Needs complex configuration** for simple installations[^7][^8]

## Implementation Steps

1. **Update your `pyproject.toml`** with the configuration I provided
2. **Test locally**: `uvx --from . mcp-github-projects-mweichert`
3. **Add installation scripts** to your repository
4. **Set up GitHub Actions** for automated releases (optional)
5. **Update your README** with the installation section I created

## Key Benefits of This Approach

- **Simple for users**: One-line installation with your script
- **GitHub-only**: No PyPI account required
- **Version control**: Works with tags and branches
- **Automated**: Can be fully automated with GitHub Actions
- **Discoverable**: Clear installation instructions in your repository


## Alternative Approaches Considered

I also evaluated GitHub Package Registry and other options, but they all require more complex setup and authentication. The direct Git installation approach provides the best balance of simplicity and functionality for your GitHub-only publishing requirement.

This solution gives you approximately 90% of the convenience of PyPI publishing while maintaining your preference for GitHub-only distribution. Users get a simple installation process, and you maintain full control over your package distribution through GitHub.

<div style="text-align: center">⁂</div>

[^1]: https://github.com/arclio/github-projects-mcp

[^2]: https://pypi.org/project/mcp-github/

[^3]: https://docs.github.com/en/packages/learn-github-packages/publishing-a-package

[^4]: https://docs.github.com/en/packages/learn-github-packages/about-permissions-for-github-packages

[^5]: https://docs.gitlab.com/user/packages/pypi_repository/

[^6]: https://docs.github.com/packages/working-with-a-github-packages-registry/working-with-the-container-registry

[^7]: https://xebia.com/blog/how-to-install-python-packages-from-an-internal-package-registry-with-uv/

[^8]: https://github.com/astral-sh/uv/issues/8352

[^9]: https://github.com/mweichert/github-projects-mcp/tree/add-milestone-tools

[^10]: https://adevait.com/software/publish-private-npm-packages-with-github-package-registry

[^11]: https://docs.astral.sh/uv/guides/package/

[^12]: https://www.paigeniedringhaus.com/blog/automatically-publish-a-repo-as-a-py-pi-library-with-git-hub-actions/

[^13]: https://www.reddit.com/r/Python/comments/1cyj6w6/how_to_publish_a_python_package_with_github/

[^14]: https://docs.astral.sh/uv/guides/tools/

[^15]: https://stackoverflow.com/questions/26708889/serving-a-python-package-from-github-on-pypi

[^16]: https://packaging.python.org/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/

[^17]: https://github.com/astral-sh/uv/issues/10122

[^18]: https://packaging.python.org/tutorials/packaging-projects/

[^19]: https://dev.to/abdellahhallou/create-and-release-a-private-python-package-on-github-2oae

[^20]: https://github.com/astral-sh/uv/issues/7345

[^21]: https://www.youtube.com/watch?v=NMQwzI9hprg

[^22]: https://github.com/astral-sh/uv/issues/8199

[^23]: https://docs.github.com/packages/working-with-a-github-packages-registry/working-with-the-nuget-registry

[^24]: https://pypi.org/project/uvx/

[^25]: https://docs.github.com/en/packages/working-with-a-github-packages-registry

[^26]: https://github.com/astral-sh/uv

[^27]: https://docs.github.com/en/packages/learn-github-packages/introduction-to-github-packages

[^28]: https://www.reddit.com/r/Python/comments/1guf2fh/if_you_use_uv_what_are_your_use_cases_for_uvx/

[^29]: https://docs.gitlab.com/user/packages/package_registry/pypi_cosign_tutorial/

[^30]: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/

[^31]: https://docs.astral.sh/uv/pip/packages/

[^32]: https://github.com/astral-sh/uv/issues/2418

[^33]: https://github.com/astral-sh/uv/issues/8244

[^34]: https://github.com/pypa/pip/issues/12081

[^35]: https://thisdavej.com/packaging-python-command-line-apps-the-modern-way-with-uv/

[^36]: https://stackoverflow.com/questions/32688688/how-to-write-setup-py-to-include-a-git-repository-as-a-dependency

[^37]: https://www.reddit.com/r/learnpython/comments/1it1on3/optimum_integration_of_uv_github_and_pycharm_to/

[^38]: https://python-poetry.org/docs/pyproject/

[^39]: https://docs.astral.sh/uv/concepts/projects/dependencies/

[^40]: https://xebia.com/blog/how-to-publish-a-python-package-to-a-gitlab-package-registry-using-uv/

[^41]: https://github.com/pypa/setuptools/discussions/3947

[^42]: https://github.com/astral-sh/uv/issues/12713

[^43]: https://docs.astral.sh/uv/guides/integration/github/

[^44]: https://github.com/orgs/community/discussions/154459

[^45]: https://docs.readthedocs.com/platform/stable/guides/private-python-packages.html

[^46]: https://github.com/phihung/tomlscript

[^47]: https://lobehub.com/mcp/achimstruve-mcp-python-testing

[^48]: https://hackernoon.com/automate-python-package-publishing-with-github-actions

[^49]: https://stackoverflow.com/questions/62983756/what-is-pyproject-toml-file-for

[^50]: https://github.com/modelcontextprotocol/python-sdk

[^51]: https://www.reddit.com/r/learnpython/comments/1lmpbtu/question_uv_uvx_install_tool_from_github_repo_and/

[^52]: https://www.firecrawl.dev/blog/fastmcp-tutorial-building-mcp-servers-python

[^53]: https://docs.github.com/en/packages/managing-github-packages-using-github-actions-workflows/publishing-and-installing-a-package-with-github-actions

[^54]: https://dagster.io/blog/untangling-python-packages-part-2

[^55]: https://johnfraney.ca/blog/how-to-publish-a-python-package-with-poetry-and-github-actions/

[^56]: https://pypi.org/project/mcp-pypi/

[^57]: https://github.com/marketplace/actions/pypi-publish

[^58]: https://lobehub.com/mcp/zakahan-pypreader-mcp

[^59]: https://playbooks.com/mcp/arclio-github-projects

[^60]: https://stackoverflow.com/questions/79344035/how-to-add-requirements-txt-to-uv-environment

[^61]: https://github.com/modelcontextprotocol/create-python-server

[^62]: https://docs.astral.sh/uv/getting-started/installation/

[^63]: https://lobehub.com/mcp/arclio-github-projects-mcp

[^64]: https://github.com/astral-sh/uv/issues/7349

[^65]: https://awslabs.github.io/mcp/installation

[^66]: https://ppl-ai-code-interpreter-files.s3.amazonaws.com/web/direct-files/f3d21837f8f3195bf835d59c4f883afa/b4fc7936-9101-41a1-b1e3-72d87c8412a0/785716c6.md

[^67]: https://ppl-ai-code-interpreter-files.s3.amazonaws.com/web/direct-files/f3d21837f8f3195bf835d59c4f883afa/d49c1031-157a-4203-84c2-6c6b5a8a98cd/2dcb9df9.toml

[^68]: https://ppl-ai-code-interpreter-files.s3.amazonaws.com/web/direct-files/f3d21837f8f3195bf835d59c4f883afa/b54aaa07-5df2-452b-a9ff-f3a3e3462daf/50d51a23.ps1

[^69]: https://ppl-ai-code-interpreter-files.s3.amazonaws.com/web/direct-files/f3d21837f8f3195bf835d59c4f883afa/b54aaa07-5df2-452b-a9ff-f3a3e3462daf/043df5bd.sh

[^70]: https://ppl-ai-code-interpreter-files.s3.amazonaws.com/web/direct-files/f3d21837f8f3195bf835d59c4f883afa/55f309d0-a544-4678-91a2-d77373cb7d9b/48ffc515.md

[^71]: https://ppl-ai-code-interpreter-files.s3.amazonaws.com/web/direct-files/f3d21837f8f3195bf835d59c4f883afa/55f309d0-a544-4678-91a2-d77373cb7d9b/dc8fff53.yml

