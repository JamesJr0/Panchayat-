if [ -z $UPSTREAM_REPO ]
then
  echo "Cloning main Repository"
  git clone https://github.com/sbrkk/MsoneSG-Updated.git /MsoneSG-Updated
else
  echo "Cloning Custom Repo from $UPSTREAM_REPO "
  git clone $UPSTREAM_REPO /MsoneSG-Updated
fi
cd /MsoneSG-Updated
pip3 install -U -r requirements.txt
echo "#AbOutMe_DK........."
python3 bot.py
