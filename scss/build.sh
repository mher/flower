set -euxo pipefail

BOOTSTRAP_VERSION="${1:-5.2.3}"
BOOTSTRAP_ZIP="v$BOOTSTRAP_VERSION.zip" 
BOOTSTRAP_DIR="bootstrap-$BOOTSTRAP_VERSION"

cd "$(git rev-parse --show-toplevel)"

if [ -f $BOOTSTRAP_ZIP ]; then
  rm $BOOTSTRAP_ZIP
fi

if [ ! -d $BOOTSTRAP_DIR ]; then
	wget https://github.com/twbs/bootstrap/archive/refs/tags/$BOOTSTRAP_ZIP
	unzip $BOOTSTRAP_ZIP
	rm $BOOTSTRAP_ZIP
fi

cp ./scss/flower.scss $BOOTSTRAP_DIR/scss/flower.scss
(cd $BOOTSTRAP_DIR && npm install &&
 sass scss/flower.scss dist/css/bootstrap.min.css --style=compressed && npm run js)

cp $BOOTSTRAP_DIR/dist/css/bootstrap.min.css ./flower/static/css/
cp $BOOTSTRAP_DIR/dist/css/bootstrap.min.css.map ./flower/static/css/
cp $BOOTSTRAP_DIR/dist/js/bootstrap.bundle.min.js ./flower/static/js/
cp $BOOTSTRAP_DIR/dist/js/bootstrap.bundle.min.js.map ./flower/static/js/