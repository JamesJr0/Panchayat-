if [ -z $UPSTREAM_REPO ]
then
  echo "Cloning main Repository"
  git clone https://github.com/CpFlicks/CpSearchXbot.git /CpSearchXbot
else
  echo "Cloning Custom Repo from $UPSTREAM_REPO "
  git clone $UPSTREAM_REPO /CpSearchXbot
fi
cd /CpSearchXbot
pip3 install -U -r requirements.txt
echo "#AbOutMe_DK........."
python3 bot.py
