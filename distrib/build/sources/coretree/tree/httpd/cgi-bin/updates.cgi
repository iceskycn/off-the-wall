#!/usr/bin/perl
#
# SmoothWall CGIs
#
# This code is distributed under the terms of the GPL
#
# (c) The SmoothWall Team

use IO::Socket;
use strict;

use lib "/usr/lib/smoothwall";
use header qw( :standard );
use update qw( :standard );
use smoothnet qw( :standard );
use smoothd qw(message);
use Time::HiRes "usleep";
use Data::Dumper;
use strict;
use warnings;

&showhttpheaders();

my (%uploadsettings, %updates);

$uploadsettings{'ACTION'} = '';
my $errormessage = '';

&getcgihash(\%uploadsettings);

my $extrahead = qq {
<script type="text/javascript">
function toggle( what )
{
	var tog = document.getElementById( what );
	if ( tog.style.display && tog.style.display != 'inline' ) {
		tog.style.display = 'inline';
	}
	else {
		tog.style.display = 'none';
	}
}
</script>
};

&openpage($tr{'updates'}, 1, $extrahead, 'maintenance');

&openbigbox('100%', 'LEFT');

if ($uploadsettings{'ACTION'} eq $tr{'upload'}) {
	my @list;
	my $return = &downloadlist();
	if ($return =~ m/^200 OK/) {
		unless (open(LIST, ">${swroot}/patches/available")) {
			$errormessage = $tr{'could not open available updates file'};
			goto ERROR;
		}
		flock LIST, 2;
		my @this = split(/----START LIST----\n/,$return);
		print LIST $this[1];
		close(LIST);
		@list = split(/\n/,$this[1]);
	} 
	else {
		unless(open(LIST, "${swroot}/patches/available")) {
			$errormessage = $tr{'could not open available updates list'};
			goto ERROR;
		}
		@list = <LIST>;
		close(LIST);
		$errormessage = $tr{'could not download the available updates list'};
	}
	unless (mkdir("/var/patches/$$",0700)) {
		$errormessage = $tr{'could not create directory'};
		goto ERROR;
	}
	unless (open(FH, ">/var/patches/$$/patch.tar.gz")) {
		$errormessage = $tr{'could not open update for writing'};
		goto ERROR;
	}
	flock FH, 2;
	print FH $uploadsettings{'FH'};
	close(FH);

	my $md5sum;
	chomp($md5sum = `/usr/bin/md5sum /var/patches/$$/patch.tar.gz`);
	my $found = 0;
	my ($id,$md5,$title,$description,$date,$url);
	foreach (@list) {
		chomp();
		($id,$md5,$title,$description,$date,$url) = split(/\|/,$_);
		if ($md5sum =~ m/^$md5\s/) {
			$found = 1;
			last;
		}
	}
	unless ($found == 1) {
		$errormessage = $tr{'this is not an authorised update'};
		goto ERROR;
	}
	unless (system("cd /var/patches/$$ && /usr/bin/tar xvfz patch.tar.gz > /dev/null") == 0) {
		$errormessage = $tr{'this is not a valid archive'};
		goto ERROR;
	}
	unless (open(INFO, "/var/patches/$$/information")) {
		$errormessage = $tr{'could not open update information file'};
		goto ERROR;
	}
	my $info = <INFO>;
	close(INFO);

	open(INS, "${swroot}/patches/installed") or $errormessage = $tr{'could not open installed updates file'};
	while (<INS>) {
		my @temp = split(/\|/,$_);
		if($info =~ m/^$temp[0]/) {
			$errormessage = $tr{'this update is already installed'};
			goto ERROR;
		}
	}
	chdir("/var/patches/$$");
	print STDERR "Going for installation attempt\n";

	if (system( '/usr/bin/setuids/installpackage', $$)) {
		$errormessage = $tr{'package failed to install'};
		goto ERROR;
	}
	unless (open(IS, ">>${swroot}/patches/installed")) {
 		$errormessage = $tr{'update installed but'};
	}
	flock IS, 2;
	my @time = gmtime();
	chomp($info);

	$time[4] = $time[4] + 1;
	$time[5] = $time[5] + 1900;
	$time[3] = "0$time[3]" if ($time[3] < 10);
	$time[4] = "0$time[4]" if ($time[4] < 10);

	print IS "$info|$time[5]-$time[4]-$time[3]\n";
	close(IS);
	&log("$tr{'the following update was successfully installedc'} $title"); 
}
elsif ($uploadsettings{'ACTION'} eq $tr{'refresh update list'}) {
	my $return = &downloadlist();
	if ($return =~ m/^200 OK/) {
		unless(open(LIST, ">${swroot}/patches/available")) {
			$errormessage = $tr{'could not open available updates file'};
			goto ERROR;
		}
		flock LIST, 2;
		my @this = split(/----START LIST----\n/,$return);
		print LIST $this[1];
		close(LIST);
		
		&log($tr{'successfully refreshed updates list'});
	} 
	else {
		$errormessage = $tr{'could not download the available updates list'};
	}
}

ERROR:

open(AV, "${swroot}/patches/available") or $errormessage = $tr{'could not open the available updates file'};
while (<AV>) {
	next if $_ =~ m/^#/;
	chomp $_;
	my @temp = split(/\|/,$_);
	my ($summary) = ( $temp[3] =~ /^(.{0,80})/ );
	$updates{ $temp[ 0 ] } = { name => $temp[2], summary => $summary, description => $temp[3], date => $temp[4], info => $temp[5], size => $temp[6], md5 => $temp[1] };
}
close (AV);

open (PF, "${swroot}/patches/installed") or $errormessage = $tr{'could not open installed updates file'};
while (<PF>) {
	my @temp = split(/\|/,$_);
	$updates{$temp[0]}{'installed'} = "---";
}
close (PF);

&alertbox($errormessage);

# Display options for adding / installing etc updates

&openbox();

my $available_count = 0;
foreach my $update ( sort keys %updates ) {
	next if ( defined $updates{$update}{'installed'} );
	$available_count ++;
}

my $height = 250;

print <<END
<br/>
<div style='height: ${height}px; overflow: auto;'>
<table class='blank' style='margin:0 0 0 1em; width:95%'>
END
;

foreach my $update ( sort keys %updates ) {
	next if ( defined $updates{$update}{'installed'} );
	print <<END
<tr>
	<td style='width: 15%;' ><a href='$updates{$update}{'info'}' onclick='window.open(this.href); return false'>$updates{$update}{'name'}</a></td>
	<td onClick="toggle('update-$update');" class='expand' title='Click to expand/hide'>$updates{$update}{'summary'}...</td>
	<td style='width: 10%; text-align:right'>$updates{$update}{'date'}</td>
</tr>
<tr>
	<td colspan='3' style='padding-left:2em'>
	<table class='expand' id='update-$update' style='display:none'>
	<tr>
		<td>$updates{$update}{'description'}</td>
	</tr>	
	</table></td>
</tr>
END
;
}

print <<END
<tr>
	<td></td>
</tr>
</table>
END
;

my $installed_count = 0;
foreach my $update ( sort keys %updates ) {
	next if ( not defined $updates{$update}{'installed'} );
	$installed_count ++;
}

if ( $installed_count > 0 ) {
	print <<END
		<p style='margin:0 0 0 1em'><strong>$tr{'installed updates'}</strong></p>
		<p style='margin:.5em 0 0 0; color: #808080; text-align:center'>
			The following updates have already been applied to your Smoothwall Express system.</p>
END
;
}

print <<END
<table class='blank' style='margin:0 0 0 1.5em; width:95%'>
END
;

foreach my $update ( sort keys %updates ) {
	next if ( not defined $updates{$update}{'installed'} );
	print <<END
<tr>
	<td style='width: 15%;' ><a style='color: #808080;' href='$updates{$update}{'info'}' onclick='window.open(this.href); return false'>$updates{$update}{'name'}</a></td>
	<td onClick="toggle('update-$update');" class='expand' style='color: #8080ff;' title='Click to expand/hide'>$updates{$update}{'summary'}...</td>
	<td style='width: 10%; text-align: right; color:#808080' >$updates{$update}{'date'}</td>
</tr>
<tr>
	<td colspan='3' style='padding-left:2em'>
		<table class='expand' id='update-$update' style='display:none'>
		<tr>
			<td style='color: #808080;' >$updates{$update}{'description'}</td>
		</tr>	
		</table>
		<!-- <script type="text/javascript">toggle('update-$update');</script> --></td>
</tr>
END
;
}

print <<END
<tr>
	<td></td>
</tr>
</table>
</div>
END
;

&closebox();
&openbox();

print <<END
<table class='blank'>
<tr>
	<td id='progressbar'>
		<table class='progressbar' style='width: 380px;'>
		<tr>
			<td id='progress' class='progressbar' style='width: 1px;'>&nbsp;</td>
			<td class='progressend'>&nbsp;</td>
		</tr>
		</table>
		<span id='status'></span></td>
	<td>&nbsp;</td>
	
	<td style='width: 350px; text-align: right;'>
		<form action='/cgi-bin/updates.cgi' method='post'><div>
		<input type='submit' name='ACTION' value='$tr{'refresh update list'}'>
		<input type='submit' name='ACTION' value='$tr{'update'}'></div></form></td>
	<td style='text-align: right;' id='actionsection'></td>
</tr>
</table>
END
;

&closebox();

print <<END
	<div id='manualinstall'>
END
;

&openbox( $tr{'install new update'} );

print <<END
$tr{'to install an update'}
<form method='post' action='/cgi-bin/updates.cgi' enctype='multipart/form-data'>
	<table class='blank'>
	<tr>
		<td>$tr{'upload update file'}</td>
		<td><input type="file" name="FH"> <input type='submit' name='ACTION' value='$tr{'upload'}'></td>
	</tr>
	</table>
</form>
END
;

&closebox();

print <<END
</div>
<script type="text/javascript">
	var add = "<input type='button' value='Advanced >>' onClick=\\"toggle('manualinstall');\\">";
	document.getElementById('actionsection').innerHTML += add;
	toggle('manualinstall');
</script>
END
;

&closebigbox();


# update downloads etc need to be dealt with at the end of the page (otherwise
# we would find ourselves with a blank page that doesn't seem to be doing a 
# great deal.
# Since the updates are "running" in the background all we "need" to do is 
# periodically test for updates


# firstly, simulate the action of the "closepage()" function, but ommit
# the </html> tags

&closepage( "update" );

if ($uploadsettings{'ACTION'} eq "$tr{'update'}" ) {
	use lib "/usr/lib/smoothwall/";

	print STDERR "Performing Update\n";

	# determine the list of updates we currently require.

	my %required;
	
	foreach my $update ( sort keys %updates ) {
		next if ( defined $updates{$update}->{'installed'} );
		$required{ $update } = $updates{$update};
	}

	# Get the # of updates to fetch
	my $updatesNeeded = scalar(keys %required);
<<<<<<< HEAD
	if ( $updatesNeeded == 0 ){
		print <<END
<script>
	document.getElementById('status').innerHTML = "All updates installed";
</script>
END
;		
	} else {
		my $status = "System requires ".$updatesNeeded." update(s)";
		print STDERR "System requires ".$updatesNeeded." update(s)\n";

		print <<END
<script>
	document.getElementById('status').innerHTML = "$status";
=======
	if ( $updatesNeeded == 0 ) {
		&progressReport ( "All updates installed" );
	}
	else {
		&progressReport ( "System requires ".$updatesNeeded." update(s)" );

		print <<END
<script type="text/javascript">
>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5
	document.getElementById('progress').style.width = '1px';
	document.getElementById('progress').style.background = '#a0a0ff';
</script>
END
<<<<<<< HEAD
;		
=======
;
>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5

		# the progress bar is 600pixels wide
		# hence we need the following bits of information.

		my $width_per_update = ( 600 / ($updatesNeeded) );
		my $complete = 0;

		sub update
		{
			my ( $percent ) = @_;
			my $distance = ( $complete * $width_per_update ) + int( int( $width_per_update / 100 ) * $percent );
			$distance = 1 if ( $distance <= 0 );

			print <<END
<script type="text/javascript">
	document.getElementById('progress').style.width = '${distance}px';
</script>
END
;
		}
	
		my $error;
<<<<<<< HEAD

		# Fetch each in turn
		foreach my $req ( sort keys %required ){
			print STDERR "Download update #$req ($required{$req}{'name'})\n";
			$status = "Download update #$req ($required{$req}{'name'})";

			print <<END
<script>
	document.getElementById('status').innerHTML = "$status";
</script>
END
;
=======
		my $filename;
		my $req;

		# Fetch each update in turn
		foreach my $req ( sort keys %required ) {
			&progressReport ( "Download update #$req ($required{$req}{'name'})" );
			&usleep ( 250000 );
>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5

			my ( $down, $percent, $speed );
		
			my $uri = "http://downloads.smoothwall.org/updates/3.1/";
			my $filename = "3.1-$required{$req}{'name'}.tar.gz";
	
			# Start the DL in the background, logging to /var/patches/pending/*.log
			&download( $uri, $filename );

			my $stop = 0;

			# Monitor the download.
			do { 
				# Get wget's progress
				( $down, $percent, $speed, $required{$req}{'file'} ) = &progress( $filename );

				my $distance = ( $complete * $width_per_update ) + int( ( $width_per_update / 100 ) * $percent );
				$distance = 1 if ( $distance <= 0 );

				print <<END
<<<<<<< HEAD
<script>
=======
<script type="text/javascript">
>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5
	document.getElementById('progress').style.width = '${distance}px';
</script>
END
;
<<<<<<< HEAD

				if ( $percent eq "100%" ){
					$stop = 1;
				} elsif( not defined $percent or $percent eq "" ){
					$stop = -1;
				} else {
					$stop = 0;
				}
				
				sleep( .25 ); 
			} while ( $stop == 0 );
=======
				print STDERR "$filename ${percent}% complete\n";

				if ( $percent eq "100" ) {
					$stop = 1;
				}
				elsif ( not defined $percent or $percent eq "" ) {
					&progressReport ( "Update #$req NOT fetched; wget probably aborted\n");
					&progressReport ( "Updates: could not download $filename; aborted. Only $complete of $updatesNeeded fetched" );
					goto CLOSEHTML;
				}
				else {
					$stop = 0;
				}
				&usleep ( 100000 ); 
			}
			while ( $stop == 0 );
>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5

			# Get wget's final progress
			( $down, $percent, $speed, $required{$req}->{'file'} ) = &progress( $filename );
			print STDERR "Update #$req fetched ($percent):\n    $required{$req}->{'md5'}\n    ($required{$req}->{'size'})\n$required{$req}->{'file'}\n";

			# Bump completed count
			$complete++;
			my $comp = $width_per_update * $complete; 

			print <<END
<<<<<<< HEAD
<script>
=======
<script type="text/javascript">
>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5
	document.getElementById('progress').style.width = '${comp}px';
</script>
END
;
<<<<<<< HEAD

=======
>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5
		}

		print STDERR "$complete of $updatesNeeded fetched\n";

<<<<<<< HEAD
		if ( $error eq "" ){
			foreach my $req ( sort keys %required ){
				$status = "Installing update $req";
				print <<END
<script>
	document.getElementById('status').innerHTML = "$status";
</script>
END
;
				use Data::Dumper;
				print STDERR Dumper $required{$req};
			 	my $worked = apply( $required{$req}->{'file'} );

				if ( not defined $worked ){
					print <<END
<script>
	document.getElementById('status').innerHTML = "$errormessage";
</script>
END
;
					$error = $errormessage;
					last;
				} 
			}
		}

		if ( $error ne "" ){
			print <<END
<script>
	document.getElementById('status').innerHTML = "One or more updates failed to install - upgrade aborted";
=======
		foreach $req ( sort keys %required ) {
			&progressReport ( "Installing update $req" );

			print STDERR Dumper $required{$req};
		 	my $worked = apply( $required{$req}->{'file'} );

			if ( not defined $worked ) {
				&progressReport ("$errormessage");
				$error = $errormessage;
				last;
			} 
		}

		if ($error) {
			&progressReport ("Update $req failed to install - update aborted.");

			print <<END
<script type="text/javascript">
>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5
	document.getElementById('progress').style.width = '1px';
	document.getElementById('progress').style.background = 'none';
</script>
END
<<<<<<< HEAD
;	
		} else {
			print <<END
<script>
	document.getElementById('status').innerHTML = "Updates Installed";
=======
;
		}
		else {
			&progressReport ("Updates installed.");

			print <<END
<script type="text/javascript">
>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5
	document.getElementById('progress').style.background = 'none';
	document.location = "/cgi-bin/updates.cgi";
</script>
END
<<<<<<< HEAD
;	
=======
;

>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5
		}		
	}

}

print <<END
</body>
</html>
END
;


sub apply
{
	my ( $f ) = @_;
	print STDERR "Applying Patch $f\n";
	
<<<<<<< HEAD
	unless (mkdir("/var/patches/$$",0700))
	{
		$errormessage = $tr{'could not create directory'};
		print STDERR "returning $errormessage\n";
		tidy();
		return undef;
	}
	unless (open(FH, ">/var/patches/$$/patch.tar.gz"))
	{
		$errormessage = $tr{'could not open update for writing'};
		print STDERR "returning $errormessage\n";
=======
	unless (mkdir("/var/patches/$$",0700)) {
		$errormessage = $tr{'could not create directory'} +"/var/patches/$$";
		&progressReport ( "apply() failed: $errormessage" );
		tidy();
		return undef;
	}

	unless (open(FH, ">/var/patches/$$/patch.tar.gz")) {
		$errormessage = $tr{'could not open update for writing'} +"/var/patches/$$/patch.tar.gz";
		&progressReport ( "apply() failed: $errormessage" );
>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5
		tidy();
		return undef;
	}

	print STDERR "Writing /var/patches/$$/patch.tar.gz\n";
	
	if ( defined $f ) {
		use File::Copy;
		move( $f, "/var/patches/$$/patch.tar.gz" );
	}
	else {
		flock FH, 2;
		print FH $uploadsettings{'FH'};
		close(FH);
	}

	my $md5sum;
	chomp($md5sum = `/usr/bin/md5sum /var/patches/$$/patch.tar.gz`);
<<<<<<< HEAD
=======
	if ($md5sum eq "d41d8cd98f00b204e9800998ecf8427e") {
		$errormessage = "patch.tar.gz is empty?!? (MD5 sum = d41d8...8427e)";
		&progressReport ( "apply() failed: $errormessage" );
		tidy();
		return undef;
	}
>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5
	my $found = 0;
	my ($id,$md5,$title,$description,$date,$url);
	print STDERR "looking for md5\n";

	unless(open(LIST, "${swroot}/patches/available")) {
		$errormessage = $tr{'could not open available updates list'};
		print STDERR "returning $errormessage\n";
		tidy();
		return undef;
	}
	my @list = <LIST>;
	close(LIST);

	foreach (@list) {
		chomp();
		($id,$md5,$title,$description,$date,$url) = split(/\|/,$_);
<<<<<<< HEAD
print STDERR "Checking MD5 Sum for $f $md5sum against $md5 ($title)\n";
		if ($md5sum =~ m/^$md5\s/)
		{
=======
		&progressReport ( "apply(): compare MD5 Sum of $f ($md5sum) against $title ($md5)" );

		if ($md5sum =~ m/^$md5\s/) {
>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5
			$found = 1;
			last;
		}
	}
<<<<<<< HEAD
print STDERR "Checking Authority\n";
	unless ($found == 1)
	{
		$errormessage = $tr{'this is not an authorised update'};
		print STDERR "$md5 $errormessage";
		tidy();
		return undef;
	}
print STDERR "Attempting Tar Operation\n";
	unless (system("/usr/bin/tar", "xfz", "/var/patches/$$/patch.tar.gz", "-C", "/var/patches/$$") == 0)
	{
=======
	unless ($found == 1) {
		$errormessage = $tr{'this is not an authorised update'} +"; the md5sums do not match";;
		&progressReport ( "apply(): $md5 $errormessage" );
		tidy();
		return undef;
	}
	&progressReport ( "apply(): unpack patch tarball..." );

	unless (system("/usr/bin/tar", "xfz", "/var/patches/$$/patch.tar.gz", "-C", "/var/patches/$$") == 0) {
>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5
		$errormessage = $tr{'this is not a valid archive'};
		print STDERR "$errormessage";
		tidy();
		return undef;
	}
<<<<<<< HEAD
print STDERR "Attempting to extract information file\n";
	unless (open(INFO, "/var/patches/$$/information"))
	{
=======
	&progressReport ( "apply(): get information file..." );

	unless (open(INFO, "/var/patches/$$/information")) {
>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5
		$errormessage = $tr{'could not open update information file'};
		print STDERR $errormessage;
		tidy();
		return undef;
	}
	my $info = <INFO>;
	close(INFO);
<<<<<<< HEAD
print STDERR "Checking status of installed updates\n";
	open(INS, "${swroot}/patches/installed") or $errormessage = $tr{'could not open installed updates file'};
	while (<INS>)
	{
=======

	&progressReport ("apply(): already installed?");

	unless (open(INS, "${swroot}/patches/installed")) {
		$errormessage = $tr{'could not open installed updates file'};
		&progressReport ( "apply() failed: $errormessage" );
		tidy();
		return undef;
	}

	while (<INS>) {
>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5
		my @temp = split(/\|/,$_);
		if($info =~ m/^$temp[0]/) {
			$errormessage = $tr{'this update is already installed'};
			print STDERR $errormessage;
			tidy();
			return undef;
		}
	}
	chdir("/var/patches/$$");
	
<<<<<<< HEAD
	if (system( '/usr/bin/setuids/installpackage', $$))
	{
=======
	&progressReport ("apply(): run installpackage to install the update");

	if (system( '/usr/bin/setuids/installpackage', $$)) {
>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5
		$errormessage = $tr{'smoothd failure'};
		tidy();
		return undef;
	}
	
	unless (open(IS, ">>${swroot}/patches/installed")) {
<<<<<<< HEAD
 		$errormessage = $tr{'update installed but'}; }
=======
 		$errormessage = $tr{'update installed but'};
		&progressReport ( "apply() failed: $errormessage" );
		tidy();
		return undef;
	}

>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5
	flock IS, 2;
	my @time = gmtime();
	chomp($info);
	$time[4] = $time[4] + 1;
	$time[5] = $time[5] + 1900;
	$time[3] = "0$time[3]" if ($time[3] < 10);
	$time[4] = "0$time[4]" if ($time[4] < 10);
	print IS "$info|$time[5]-$time[4]-$time[3]\n";
	close(IS);
	tidy();
	
	&log("$tr{'the following update was successfully installedc'} $title"); 
}

sub tidy
{
	print STDERR "Tidying up\n";

	opendir(CUSTOM, "/var/patches/$$/");
	my @files = readdir (CUSTOM);
	closedir(CUSTOM);

<<<<<<< HEAD
	foreach my $file (@files)
	{
		print STDERR "Unlinking $file\n";
		next if ( $file =~ /^\..*/ );
		unlink "/var/patches/$$/$file";
	}

	print STDERR "Removing directory $$\n";
=======
	foreach my $file (@files) {
		&progressReport ( "tidy(): unlinking $file" );
		next if ( $file =~ /^\..*/ );
		unlink "/var/patches/$$/$file";
	}
	&progressReport ( "tidy(): remove directory $$" );
>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5
	rmdir "/var/patches/$$";
}


<<<<<<< HEAD
=======
sub progressReport
{
	my ($statusStr) = @_;
	print <<END
<script type="text/javascript">
	document.getElementById('status').innerHTML = "$statusStr";
</script>
END
;
	print STDERR "$statusStr\n";
	&usleep ( 250000 );
}
>>>>>>> f57ce9f3ea6fcdfeaf84cc0d44868f10eebd2fe5
