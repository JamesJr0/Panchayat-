if [ -z $UPSTREAM_REPO ]
then
  echo "Cloning main Repository"
  git clone https://github.com/CpFlicks/ProSearchFather.git /ProSearchFather
else
  echo "Cloning Custom Repo from $UPSTREAM_REPO "
  git clone $UPSTREAM_REPO /ProSearchFather
fi
cd /ProSearchFather
pip3 install -U -r requirements.txt
echo "Officially Created By @AbOutMe_DK For Team @ProSearchFather! Bot is Up... Checking For Errors.."
python3 bot.py
