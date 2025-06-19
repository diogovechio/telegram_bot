# Pedro Leblon Bot

## Installation

### Dependencies

This project requires several Python dependencies which are listed in the `requirements.txt` file.

To ensure secure installation of dependencies, we've provided scripts that include trusted host flags for PyPI:

#### Windows Users

Run the `install_dependencies.bat` script:

```
install_dependencies.bat
```

#### Linux/Mac Users

Make the script executable and run it:

```bash
chmod +x install_dependencies.sh
./install_dependencies.sh
```

#### Manual Installation

If you prefer to install dependencies manually, use:

```bash
pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

## Configuration

Before running the bot, make sure to configure:

1. `bot_configs.json` - General bot configuration
2. `secrets.json` - API keys and tokens

## Running the Bot

To start the bot, run:

```bash
python run.py
```