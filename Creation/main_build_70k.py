import sys
sys.path.append('D:\\Github\\GridWorkbench\\src\\')
# sys.path.append('D:\\Github\\GridWorkbench\\src\\') # linked to github

from do_sub_planning_Nordic import do_sub_planning_Sweden
from do_transmission_preplanning_Nordic_modified import do_transmission_preplanning_Sweden
from do_transmission_planning_Nordic import do_transmission_planning_Sweden

do_sub_planning_Sweden()
do_transmission_preplanning_Sweden()
do_transmission_planning_Sweden()

from do_sub_planning_70k import do_sub_planning_70k
from do_transmission_planning_70k import do_transmission_planning_70k
from do_transmission_preplanning_70k import do_transmission_preplanning_70k
#
# do_sub_planning_70k()
# do_transmission_preplanning_70k()
# do_transmission_planning_70k()