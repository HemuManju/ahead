import yaml
from pathlib import Path
from visualization.visualise import gate_output

from utils import skip_run

# The configuration file
config_path = Path(__file__).parents[1] / 'src/config.yml'
config = yaml.load(open(str(config_path)), Loader=yaml.SafeLoader)

with skip_run('run', 'Plot gate output') as check, check():
    games = [
        'asterix', 'breakout', 'centipede', 'freeway', 'ms_pacman', 'phoenix',
        'seaquest', 'space_invaders'
    ]
    games = ['phoenix', 'space_invaders']

    gate_output(games, config)
