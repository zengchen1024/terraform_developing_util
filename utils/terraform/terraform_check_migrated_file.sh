#!/bin/bash

if [ $# -ne 2 ]; then
	echo -e "this util is used to check files migrated from one provider to another\n"
	echo -e "usage: $0 src_cloud_alias dest_cloud_alias\n"
	echo -e "Note: please run 'git add .' before running this script\n"
	exit 1
fi

. "$(dirname $(which $0))/common.sh"
get_config="$(dirname $(which $0))/$config_exec"

src_cloud_alias=$1
src_cloud=$($get_config name $src_cloud_alias)
test $? -ne 0 && echo "can not find cloud name: $src_cloud_alias" && exit 1
src_cloud_u=$($get_config name_of_upper $src_cloud_alias)
src_cloud_l=$($get_config name_of_long $src_cloud_alias)


dest_cloud_alias=$2
dest_cloud=$($get_config name $dest_cloud_alias)
test $? -ne 0 && echo "can not find cloud name: $dest_cloud_alias" && exit 1
dest_dir=$($get_config code_dir $dest_cloud_alias)

cur_dir=$(pwd)
cd $dest_dir

r=$(grep "$src_cloud\|$src_cloud_u\|$src_cloud_l" -n $(git status | grep "modified:\|new file:" | awk '{print $NF}'))
test -n "$r" && echo -e "\n$r\n"

cd $cur_dir
