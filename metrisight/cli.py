"""CLI entry point for MetriSight dashboard."""

import subprocess
import sys
from pathlib import Path


def main():
    """Launch the MetriSight Streamlit dashboard."""
    app_path = Path(__file__).resolve().parent.parent / "app.py"

    if not app_path.exists():
        # When installed as a package, app.py may be alongside the package
        # Try common locations
        for candidate in [
            Path(sys.prefix) / "app.py",
            Path(__file__).resolve().parent / "app.py",
        ]:
            if candidate.exists():
                app_path = candidate
                break
        else:
            print(
                "Error: Could not find app.py. "
                "Run 'streamlit run app.py' from the project directory instead."
            )
            sys.exit(1)

    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        pass
    except FileNotFoundError:
        print("Error: Streamlit is not installed. Run: pip install streamlit")
        sys.exit(1)


if __name__ == "__main__":
    main()
