#!/usr/bin/perl

# Script to illustrate how to parse a simple XML file
# and dump its contents in a Perl hash record.

#use strict;
use XML::Simple;
use Data::Dumper;

my $what = $ARGV[0];
my $which = $ARGV[1];

if ( ! -f "usb-modeswitch-versions.xml" )
{
  system("wget http://www.draisberghof.de/usb_modeswitch/usb-modeswitch-versions.xml");
}

my $modeswitch = XMLin('usb-modeswitch-versions.xml', KeyAttr => {target => 'URL'});

unlink("usb-modeswitch-versions.xml");

my $i;
for ($i=0; $i<@{$modeswitch->{"package"}}; $i++)
{
  if ($modeswitch->{"package"}->[$i]->{'name'} eq $which)
  {
    print $modeswitch->{"package"}->[$i]->{$what};
    exit 0;
  }
}
