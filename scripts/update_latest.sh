#!/bin/bash
script_path=`dirname "$(readlink -f "$0")"`
project_path=`dirname $script_path`
results_path="${project_path}/results"
result_path=`ls results| grep '-'| tail -n1`
latest_path=$results_path/latest
if [[ -d "$latest_path" ]]
then
  rm "$latest_path"
fi
ln -s $result_path $latest_path

