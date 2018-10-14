# PlexPostProcess
Made so i can get coronation street back on track; essentially once Plex has made a recording in the DVR i want it to do a few things as a post process. It performs as follows:

* Detect duplicates and delete if necessary
* If it's a radio recording simply extract the .mp3 file as not interested in video stream
* Attempt to perform commercial skipping (inbuilt no good as running on FreeBSD)
* Transcode to Apple compatible format (this is simply how i like to keep my library)
* Move to a filename such that Coronation Street records well

# Installation Of Dependencies

You need a number of packages installed; I'm running on FreeNas 11.0 and this gives me a number of very big headaches as the version of HandBrake currently deployed into the repos for FreeBSD is broken on my platform so i have to maintain my own version of HandBrake. Comskip isn't available OOTB so this needs to be deployed seperately. You need the wonderful PlexComskip package installed as this is used for commercial skipping as well.

## Comskip

If doing this on FreeNAS 11.0 you will need to do the following AFTER installing HandBrake from master branch.

<pre>
cd /usr/local
git clone git://github.com/erikkaashoek/Comskip
cd Comskip
git checkout master
PKG_CONFIG_PATH="/usr/local/HandBrakeGit/build/contrib/lib/pkgconfig" ./configure
gmake install
</pre>

## (HandBrake (depends lame-3.100))

Only do this if you really really have to :( try with the package tree maintainers version first.

<pre>
cd /usr/local
git clone https://github.com/HandBrake/HandBrake.git HandBrakeGit
cd HandBrakeGit
./configure CXX=/usr/local/bin/clang++ CC=/usr/local/bin/clang LDFLAGS="-L/usr/local/lib -L/usr/local/HandBrake/build/contrib/lib -DLIBICONV_PLUG" CXXFLAGS="-std=c++14 -I/usr/local/HandBrake/build/contrib/include -mfpmath=sse -msse2 -DLIBICONV_PLUG -I/usr/local/include" CFLAGS=" -I/usr/local/include -I/usr/local/HandBrake/build/contrib/include -I/usr/local/include/opus -mfpmath=sse -msse2 -DLIBICONV_PLUG"  --disable-x265 --force
cd build/
gmake CXX=/usr/local/bin/clang++
</pre>

# PlexComskip

<pre>
cd /usr/local
git clone https://github.com/ekim1337/PlexComskip.git
</pre>

# Configuration

## Plex Comskip

Edit `/usr/local/PlexComskip/PlexComskip.conf` with the following:

<pre>
[Helper Apps]

# Path to the comskip binary.
comskip-path: /usr/local/bin/comskip

# Path to the comskip INI file. Defaults to the same directory as the PlexComskip script.
# comskip-ini-path: /usr/local/PlexComskip/comskip.ini

# Path to the ffmpeg binary.
ffmpeg-path: /usr/local/bin/ffmpeg

# Nice level. Used for file copies, comskip analysis, and ffmpeg processing. 0 (default, full priority) - 20 (most nice)
nice-level: 0

[Logging]

# Log file location.
logfile-path: /var/log/PlexComskip/PlexComskip.log

# Split the log output to the console? Useful for debugging.
console-logging: True

[File Manipulation]

# Specify a temp directory for interstitial files. This should be local, fast, and have enough free space for ~2x your largest video. Defaults to system temp location.
# temp-root: /tmp

# Should we copy the original file to the temp directory? Useful if disk access to the original is slower than your temp location. Defaults to False.
copy-original: False

# Always save the intermediate files? Useful for debugging. Defaults to False.
save-always: False

# Save intermediate files when something goes wrong? Also useful for debugging and less space intensive. Defaults to True.
save-forensics: True
</pre>

## Scan And Transcode

This application has a config file in `/etc/defaults/sat.conf` that tells it currently how to access the database:

<pre>
[Database]
host=localhost
user=root
password=Password!
db=scan_and_transcode
</pre>

# Installation of Database

The application uses a MySQL database first create it

<pre>
CREATE DATABASE scan_and_transcode;
</pre>

then restore the database

<pre>
mysql -u root -p scan_and_transcode < sat_install.sql
</pre>
