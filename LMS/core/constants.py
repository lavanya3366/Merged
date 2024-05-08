
# used in courseview , customercourseregistrationview
filtered_display_list = ["active", "inactive", "all"] 
# used in managecourseregistrationrecordstatusview
manage_status_list = ["activate","inactivate"]
# used in managecourseview
manage_course_list = ["activate", "inactivate","versioning"]

#used inside custom_mixins.py [list of resource id on which these resources exists]
super_admin_resources = {1, 2, 4, 5, 6}
client_admin_resources = {1, 3, 4, 6}
client_resources = {1, 4, 6} 
'''allowed_resources:
1- LMS
2- Course Customer Registration
3- Course Enrollment
4- Courses
5- Course Management
6- Dashboard'''
course_enrollment_id = 3
course_registration_id = 2
course_management_id = 5
dashboard_id = 6