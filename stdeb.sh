#!/bin/sh

NAME=`python3 setup.py --name`
VERSION=`python3 setup.py --version`

echo ${NAME}-${VERSION}

python3 setup.py --command-packages=stdeb.command sdist_dsc
cp ./debian/* deb_dist/${NAME}-${VERSION}/debian
cd deb_dist/${NAME}-${VERSION}/
dpkg-buildpackage -rfakeroot -uc -us

#
cp ~/fand/deb_dist/python3-fand_0.0.1-1_all.deb ~/pkg/
