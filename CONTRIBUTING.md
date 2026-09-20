# Contributing to APEX

Thank you for your interest in contributing to APEX — the AI YouTube Content Agent.

## How to contribute

### Bug reports
Open an issue with:
- What you expected to happen
- What actually happened
- Your OS, Python version, and which AI provider you are using
- Relevant log output from the dashboard Audit Log tab

### Feature requests
Open an issue describing:
- The feature you want
- Why it would help channel growth or automation
- Which phase it fits (production, research, analytics, etc.)

### Pull requests
1. Fork the repo and create a branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Run the full test suite: `python tests/test_e2e.py` — all 20 must pass
4. Add tests for any new functionality
5. Commit with a clear message: `feat: add X` or `fix: resolve Y`
6. Open a pull request with a clear description

## Code standards
- Python 3.10+
- No external dependencies unless absolutely necessary
- Every new module must have at least one test in `tests/test_e2e.py`
- All approval gates must remain intact — never auto-publish without owner approval
- Copyright scanner must stay active — never weaken it

## Security
Never commit `.apex_config`, `client_secrets.json`, `youtube_token.json`, or any API key.
The `.gitignore` blocks these — do not remove those entries.

## License
By contributing, you agree your contributions are licensed under the MIT License.
The original characters (Trishul, Sandy, Libhu, Sunridge Town) remain the property of the channel creator.
