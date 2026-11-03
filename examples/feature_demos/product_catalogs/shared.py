"""Organization-wide roles referenced directly by both product catalogs."""
from myworkflow import Role

operator = Role('role.operator', '商品運用部の業務担当者', '業務担当者')
system = Role('role.system', '商品業務システム', 'システム')
