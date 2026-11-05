list(){
  local agent=${1:-DocProcessing} # DocProcessing | AskOrchestrate
  orchestrate channels list-channels --env draft --agent-name $agent
}
$@