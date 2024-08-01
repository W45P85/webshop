from django import template

register = template.Library()

@register.filter
def is_group_member(user, group_name):
    return user.groups.filter(name=group_name).exists()