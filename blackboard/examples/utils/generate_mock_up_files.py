import os

# Define mock data
projects = {
    "ProjectA": {
        "seq01": ["shot01", "shot02"],
        "seq02": ["shot01"]
    },
    "ProjectB": {
        "seq01": ["shot01", "shot02", "shot03"]
    }
}

# Mock assets to create in each shot directory
mock_assets = ["model.mb", "texture.png", "rig.ma"]
'blackboard/examples/projects/{project_name}/seq_{sequence_name}/{shot_name}/work_files'
# Base path for the mock structure
base_path = "blackboard/examples/projects"

def generate_mock_assets(projects, mock_assets, base_path: str = ''):
    for project_name, sequences in projects.items():
        for sequence_name, shots in sequences.items():
            for shot_name in shots:
                # Construct the directory path
                dir_path = os.path.join(base_path, project_name, f"seq_{sequence_name}", shot_name, "work_files")

                # Create the directory if it doesn't exist
                os.makedirs(dir_path, exist_ok=True)

                # Generate mock asset files
                for asset in mock_assets:
                    asset_path = os.path.join(dir_path, asset)
                    open(asset_path, 'a').close()  # This creates an empty file if it doesn't exist

    print("Mock asset generation complete.")

# Call the function with the mock data
generate_mock_assets(projects, mock_assets, base_path)
