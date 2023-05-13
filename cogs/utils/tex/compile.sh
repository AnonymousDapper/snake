#!/usr/bin/env sh
cd tex/staging/$1/

timeout 1m xelatex -no-shell-escape $1.tex > texout.log 2>&1

RET=$?
if [ $RET -eq 0 ];
then
 echo "";
elif [ $RET -eq 124 ];
then
 echo "Compilation timed out!";
else
    grep -A 10 -m 1 "^!" $1.log;
fi

if [ ! -f $1.pdf ];
then
  cp ../../failed.png $1.png
  exit 1
fi

timeout 20 convert -density 700 -quality 75 -depth 8 -trim +repage $1.pdf -colorspace sRGB PNG32:$1.png;
if [ $? -eq 124 ];
then
 echo "Image processing timed out!";
 cp ../../failed.png $1.png
 exit 1
fi

timeout 20 convert $1.png -bordercolor transparent -border 50 -background 'transparent' -flatten PNG32:$1.png;

if [ $? -eq 124 ]; then
  echo "Recoloring timed out!";
  cp ../../failed.png $1.png
  exit 1
fi

width=`convert $1.png -format "%[fx:w]" info:`
minwidth=1000
extra=$((minwidth-width))

if [ $extra -gt 0 ]; then
  timeout 20 convert $1.png -gravity East +antialias -splice ${extra}x -alpha set -background transparent -alpha Background -channel alpha -fx "i>${width}-5?0:a" +channel PNG32:$1.png;

  if [ $? -eq 124 ]; then
    echo "Padding timed out!";
    cp ../../failed.png $1.png
    exit 1
  fi
fi