# Project Structure Overview

## 🗂 Directory Tree

```text
.
|-- addons/
|   |-- common/
|   |   `-- itad_core/
|   |       |-- controllers/
|   |       |   |-- __init__.py
|   |       |   `-- controllers.py
|   |       |-- data/
|   |       |   |-- itad_core_system_parameters.xml
|   |       |   |-- itad_outbox_cron.xml
|   |       |   `-- itad_receipt_audit_archiving_cron.xml
|   |       |-- demo/
|   |       |   `-- demo.xml
|   |       |-- models/
|   |       |   |-- __init__.py
|   |       |   |-- fsm_order.py
|   |       |   |-- itad_config.py
|   |       |   |-- itad_outbox.py
|   |       |   |-- itad_pickup_manifest.py.DISABLED
|   |       |   |-- itad_receipt_audit_log.py
|   |       |   |-- itad_receiving_wizard.py
|   |       |   `-- models.py
|   |       |-- scripts/
|   |       |   `-- migrate_phase2_1_to_2_2.py
|   |       |-- security/
|   |       |   |-- ir.model.access.csv
|   |       |   `-- itad_core_groups.xml
|   |       |-- tests/
|   |       |   |-- __init__.py
|   |       |   |-- test_itad_config.py
|   |       |   |-- test_migration_phase2_1_to_2_2.py
|   |       |   |-- test_no_attrs_states.py
|   |       |   |-- test_outbox_idempotency.py
|   |       |   |-- test_phase1_vertical_slice.py
|   |       |   |-- test_receiving_api_compat_check.py
|   |       |   |-- test_receiving_audit_archiving.py
|   |       |   |-- test_receiving_contract_integration.py
|   |       |   |-- test_receiving_rate_limit.py
|   |       |   `-- test_receiving_wizard_hardening.py
|   |       |-- views/
|   |       |   |-- fsm_order_itad.xml
|   |       |   |-- itad_outbox_views.xml
|   |       |   |-- itad_receiving_views.xml
|   |       |   |-- templates.xml
|   |       |   `-- views.xml
|   |       |-- __init__.py
|   |       |-- __manifest__.py
|   |       `-- hooks.py
|   `-- odoo18/
|       `-- oca/
|           `-- field-service/
|               |-- base_territory/
|               |   |-- demo/
|               |   |   `-- base_territory_demo.xml
|               |   |-- i18n/
|               |   |   |-- base_territory.pot
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- it.po
|               |   |   |-- pl.po
|               |   |   |-- pt_BR.po
|               |   |   `-- tr.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- res_branch.py
|               |   |   |-- res_country.py
|               |   |   |-- res_district.py
|               |   |   |-- res_region.py
|               |   |   `-- res_territory.py
|               |   |-- readme/
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- CREDITS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   `-- USAGE.md
|               |   |-- security/
|               |   |   `-- ir.model.access.csv
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   |-- test_res_branch.py
|               |   |   |-- test_res_country.py
|               |   |   |-- test_res_district.py
|               |   |   |-- test_res_region.py
|               |   |   `-- test_res_territory.py
|               |   |-- views/
|               |   |   |-- menu.xml
|               |   |   |-- res_branch.xml
|               |   |   |-- res_country.xml
|               |   |   |-- res_district.xml
|               |   |   |-- res_region.xml
|               |   |   `-- res_territory.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice/
|               |   |-- data/
|               |   |   |-- fsm_stage.xml
|               |   |   |-- fsm_team.xml
|               |   |   |-- ir_sequence.xml
|               |   |   |-- mail_message_subtype.xml
|               |   |   `-- module_category.xml
|               |   |-- demo/
|               |   |   |-- fsm_demo.xml
|               |   |   |-- fsm_equipment.xml
|               |   |   |-- fsm_location.xml
|               |   |   `-- fsm_person.xml
|               |   |-- i18n/
|               |   |   |-- de.po
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- es_CL.po
|               |   |   |-- fieldservice.pot
|               |   |   |-- fr.po
|               |   |   |-- fr_FR.po
|               |   |   |-- it.po
|               |   |   |-- pl.po
|               |   |   |-- pt_BR.po
|               |   |   |-- pt_PT.po
|               |   |   `-- tr.po
|               |   |-- migrations/
|               |   |   |-- 18.0.2.0.0/
|               |   |   |   `-- post-migrate.py
|               |   |   |-- 18.0.4.0.0/
|               |   |   |   `-- pre-migrate-fsm-location-hierarchy.py
|               |   |   `-- 18.0.5.4.0/
|               |   |       `-- post-migrate-text-to-html.py
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_category.py
|               |   |   |-- fsm_equipment.py
|               |   |   |-- fsm_location.py
|               |   |   |-- fsm_location_person.py
|               |   |   |-- fsm_model_mixin.py
|               |   |   |-- fsm_order.py
|               |   |   |-- fsm_order_type.py
|               |   |   |-- fsm_person.py
|               |   |   |-- fsm_person_calendar_filter.py
|               |   |   |-- fsm_stage.py
|               |   |   |-- fsm_tag.py
|               |   |   |-- fsm_team.py
|               |   |   |-- fsm_template.py
|               |   |   |-- res_company.py
|               |   |   |-- res_config_settings.py
|               |   |   |-- res_partner.py
|               |   |   `-- res_territory.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- CREDITS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   |-- ROADMAP.md
|               |   |   `-- USAGE.md
|               |   |-- report/
|               |   |   `-- fsm_order_report_template.xml
|               |   |-- security/
|               |   |   |-- ir.model.access.csv
|               |   |   |-- ir_rule.xml
|               |   |   `-- res_groups.xml
|               |   |-- static/
|               |   |   |-- description/
|               |   |   |   |-- icon.png
|               |   |   |   |-- icon.svg
|               |   |   |   `-- index.html
|               |   |   `-- src/
|               |   |       `-- scss/
|               |   |           `-- team_dashboard.scss
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   |-- test_fsm_category.py
|               |   |   |-- test_fsm_equipment.py
|               |   |   |-- test_fsm_location.py
|               |   |   |-- test_fsm_order.py
|               |   |   |-- test_fsm_order_template_onchange.py
|               |   |   |-- test_fsm_person.py
|               |   |   |-- test_fsm_team.py
|               |   |   |-- test_fsm_wizard.py
|               |   |   `-- test_res_partner.py
|               |   |-- views/
|               |   |   |-- fsm_category.xml
|               |   |   |-- fsm_equipment.xml
|               |   |   |-- fsm_location.xml
|               |   |   |-- fsm_location_person.xml
|               |   |   |-- fsm_order.xml
|               |   |   |-- fsm_order_type.xml
|               |   |   |-- fsm_person.xml
|               |   |   |-- fsm_stage.xml
|               |   |   |-- fsm_tag.xml
|               |   |   |-- fsm_team.xml
|               |   |   |-- fsm_template.xml
|               |   |   |-- menu.xml
|               |   |   |-- res_config_settings.xml
|               |   |   |-- res_partner.xml
|               |   |   `-- res_territory.xml
|               |   |-- wizard/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_order_sign_wizard.py
|               |   |   |-- fsm_order_sign_wizard.xml
|               |   |   |-- fsm_wizard.py
|               |   |   `-- fsm_wizard.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_account/
|               |   |-- i18n/
|               |   |   |-- de.po
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- es_CL.po
|               |   |   |-- fieldservice_account.pot
|               |   |   |-- it.po
|               |   |   |-- pt_BR.po
|               |   |   `-- tr.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- account_move.py
|               |   |   |-- account_move_line.py
|               |   |   |-- fsm_order.py
|               |   |   `-- fsm_stage.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- CREDITS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   |-- INSTALL.md
|               |   |   `-- USAGE.md
|               |   |-- security/
|               |   |   `-- ir.model.access.csv
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fsm_account.py
|               |   |-- views/
|               |   |   |-- account_move.xml
|               |   |   |-- fsm_order.xml
|               |   |   `-- fsm_stage.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_activity/
|               |   |-- i18n/
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- es_CL.po
|               |   |   |-- fieldservice_activity.pot
|               |   |   |-- it.po
|               |   |   |-- pl.po
|               |   |   |-- pt_BR.po
|               |   |   |-- pt_PT.po
|               |   |   `-- sv.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_activity.py
|               |   |   |-- fsm_order.py
|               |   |   `-- fsm_template.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- CREDITS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   `-- USAGE.md
|               |   |-- security/
|               |   |   `-- ir.model.access.csv
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- field_service_settings_manage_templates.png
|               |   |       |-- field_service_template.png
|               |   |       |-- field_service_template_activities.png
|               |   |       |-- fsm_order_activity_tab.png
|               |   |       |-- icon.png
|               |   |       |-- icon.svg
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fsm_activity.py
|               |   |-- views/
|               |   |   |-- fsm_order.xml
|               |   |   `-- fsm_template.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_agreement/
|               |   |-- i18n/
|               |   |   |-- de.po
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- es_CL.po
|               |   |   |-- fieldservice_agreement.pot
|               |   |   |-- it.po
|               |   |   `-- pt_BR.po
|               |   |-- migrations/
|               |   |   `-- 18.0.1.1.0/
|               |   |       `-- post-migrate.py
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- agreement.py
|               |   |   |-- fsm_equipment.py
|               |   |   |-- fsm_order.py
|               |   |   `-- fsm_person.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- CREDITS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   |-- ROADMAP.md
|               |   |   `-- USAGE.md
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fsm_agreement.py
|               |   |-- views/
|               |   |   |-- agreement_view.xml
|               |   |   |-- fsm_equipment_view.xml
|               |   |   |-- fsm_order_view.xml
|               |   |   `-- fsm_person.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_availability/
|               |   |-- i18n/
|               |   |   |-- ca.po
|               |   |   |-- es.po
|               |   |   |-- fieldservice_availability.pot
|               |   |   `-- it.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_blackout_day.py
|               |   |   |-- fsm_blackout_group.py
|               |   |   |-- fsm_delivery_time_range.py
|               |   |   `-- fsm_stress_day.py
|               |   |-- readme/
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   `-- USAGE.md
|               |   |-- security/
|               |   |   `-- ir.model.access.csv
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fsm_delivery_time_range.py
|               |   |-- views/
|               |   |   |-- fsm_blackout_day_templates.xml
|               |   |   |-- fsm_delivery_time_range_templates.xml
|               |   |   |-- fsm_stress_day_templates.xml
|               |   |   `-- menu.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_calendar/
|               |   |-- i18n/
|               |   |   |-- de.po
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- fieldservice_calendar.pot
|               |   |   |-- it.po
|               |   |   `-- pt_BR.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- calendar.py
|               |   |   |-- fsm_order.py
|               |   |   `-- fsm_team.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   `-- DESCRIPTION.md
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fsm_calendar.py
|               |   |-- views/
|               |   |   |-- fsm_order.xml
|               |   |   `-- fsm_team.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_crm/
|               |   |-- i18n/
|               |   |   |-- de.po
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- es_CL.po
|               |   |   |-- fieldservice_crm.pot
|               |   |   |-- fr.po
|               |   |   |-- it.po
|               |   |   `-- pt_BR.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- crm_lead.py
|               |   |   |-- fsm_location.py
|               |   |   `-- fsm_order.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- CREDITS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   |-- INSTALL.md
|               |   |   |-- ROADMAP.md
|               |   |   `-- USAGE.md
|               |   |-- security/
|               |   |   `-- ir.model.access.csv
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fsm_crm.py
|               |   |-- views/
|               |   |   |-- crm_lead.xml
|               |   |   |-- fsm_location.xml
|               |   |   `-- fsm_order.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_equipment_stock/
|               |   |-- i18n/
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- fieldservice_equipment_stock.pot
|               |   |   |-- it.po
|               |   |   `-- pt_BR.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_equipment.py
|               |   |   |-- product_template.py
|               |   |   |-- stock_lot.py
|               |   |   |-- stock_move.py
|               |   |   `-- stock_picking_type.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- CREDITS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   |-- ROADMAP.md
|               |   |   `-- USAGE.md
|               |   |-- security/
|               |   |   `-- ir.model.access.csv
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   |-- test_fsm_equipment.py
|               |   |   `-- test_stock_move.py
|               |   |-- views/
|               |   |   |-- fsm_equipment.xml
|               |   |   |-- product_template.xml
|               |   |   |-- stock_lot.xml
|               |   |   `-- stock_picking_type.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_equipment_warranty/
|               |   |-- i18n/
|               |   |   |-- fieldservice_equipment_warranty.pot
|               |   |   |-- fr.po
|               |   |   `-- it.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   `-- fsm_equipment.py
|               |   |-- readme/
|               |   |   |-- CONTRIBUTORS.md
|               |   |   `-- DESCRIPTION.md
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fsm_equipment_warranty.py
|               |   |-- views/
|               |   |   `-- fsm_equipment.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_kanban_info/
|               |   |-- i18n/
|               |   |   |-- ca.po
|               |   |   |-- es.po
|               |   |   |-- fieldservice_kanban_info.pot
|               |   |   `-- it.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_order.py
|               |   |   `-- res_config_settings.py
|               |   |-- readme/
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   `-- USAGE.md
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fieldservice_kanban_info.py
|               |   |-- views/
|               |   |   |-- fsm_order.xml
|               |   |   `-- res_config_settings_views.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_portal/
|               |   |-- controllers/
|               |   |   |-- __init__.py
|               |   |   `-- fsm_order_portal.py
|               |   |-- demo/
|               |   |   |-- fsm_location_demo.xml
|               |   |   `-- fsm_order_demo.xml
|               |   |-- i18n/
|               |   |   |-- ca.po
|               |   |   |-- de.po
|               |   |   |-- es.po
|               |   |   |-- fieldservice_portal.pot
|               |   |   |-- fr.po
|               |   |   |-- it.po
|               |   |   |-- pt_BR.po
|               |   |   `-- sv.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   `-- fsm_stage.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   `-- DESCRIPTION.md
|               |   |-- security/
|               |   |   |-- ir.model.access.csv
|               |   |   `-- portal_security.xml
|               |   |-- static/
|               |   |   |-- description/
|               |   |   |   |-- icon.png
|               |   |   |   `-- index.html
|               |   |   `-- src/
|               |   |       |-- img/
|               |   |       |   `-- fsmorder.svg
|               |   |       `-- js/
|               |   |           `-- fsm_order_portal.esm.js
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_portal.py
|               |   |-- views/
|               |   |   |-- fsm_order_template.xml
|               |   |   |-- fsm_stage.xml
|               |   |   `-- portal_template.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_project/
|               |   |-- i18n/
|               |   |   |-- de.po
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- es_CL.po
|               |   |   |-- fieldservice_project.pot
|               |   |   |-- fr.po
|               |   |   |-- it.po
|               |   |   |-- pl.po
|               |   |   `-- pt_BR.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_location.py
|               |   |   |-- fsm_order.py
|               |   |   |-- fsm_team.py
|               |   |   |-- project.py
|               |   |   `-- project_task.py
|               |   |-- readme/
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- CREDITS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   |-- ROADMAP.md
|               |   |   `-- USAGE.md
|               |   |-- security/
|               |   |   `-- ir.model.access.csv
|               |   |-- static/
|               |   |   |-- description/
|               |   |   |   |-- icon.png
|               |   |   |   |-- icon.svg
|               |   |   |   `-- index.html
|               |   |   `-- src/
|               |   |       `-- scss/
|               |   |           `-- project_column.scss
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   |-- common.py
|               |   |   |-- test_fsm_location.py
|               |   |   |-- test_fsm_order.py
|               |   |   |-- test_project.py
|               |   |   `-- test_project_task.py
|               |   |-- views/
|               |   |   |-- fsm_location_views.xml
|               |   |   |-- fsm_order_views.xml
|               |   |   |-- fsm_team.xml
|               |   |   |-- project_task_views.xml
|               |   |   `-- project_views.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_recurring/
|               |   |-- data/
|               |   |   |-- ir_sequence.xml
|               |   |   `-- recurring_cron.xml
|               |   |-- demo/
|               |   |   |-- frequency_demo.xml
|               |   |   |-- frequency_set_demo.xml
|               |   |   `-- recur_template_demo.xml
|               |   |-- i18n/
|               |   |   |-- de.po
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- es_CL.po
|               |   |   |-- fieldservice_recurring.pot
|               |   |   |-- it.po
|               |   |   |-- pt_BR.po
|               |   |   |-- sv.po
|               |   |   `-- tr.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_frequency.py
|               |   |   |-- fsm_frequency_set.py
|               |   |   |-- fsm_order.py
|               |   |   |-- fsm_recurring.py
|               |   |   |-- fsm_recurring_template.py
|               |   |   `-- fsm_team.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- CREDITS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   |-- INSTALL.md
|               |   |   |-- ROADMAP.md
|               |   |   `-- USAGE.md
|               |   |-- security/
|               |   |   |-- ir.model.access.csv
|               |   |   |-- recurring_security.xml
|               |   |   `-- res_groups.xml
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fsm_recurring.py
|               |   |-- views/
|               |   |   |-- fsm_frequency.xml
|               |   |   |-- fsm_frequency_set.xml
|               |   |   |-- fsm_order.xml
|               |   |   |-- fsm_recurring.xml
|               |   |   |-- fsm_recurring_template.xml
|               |   |   `-- fsm_team.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_repair/
|               |   |-- data/
|               |   |   `-- fsm_order_type.xml
|               |   |-- i18n/
|               |   |   |-- de.po
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- fieldservice_repair.pot
|               |   |   |-- fr.po
|               |   |   |-- it.po
|               |   |   `-- pt_BR.po
|               |   |-- migrations/
|               |   |   `-- 18.0.2.0.0/
|               |   |       `-- post-migrate.py
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_order.py
|               |   |   |-- fsm_order_type.py
|               |   |   `-- repair_order.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- CREDITS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   |-- INSTALL.md
|               |   |   |-- ROADMAP.md
|               |   |   `-- USAGE.md
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fsm_repair.py
|               |   |-- views/
|               |   |   `-- fsm_order_view.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_repair_order_template/
|               |   |-- i18n/
|               |   |   |-- fieldservice_repair_order_template.pot
|               |   |   `-- it.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_order.py
|               |   |   `-- fsm_template.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   `-- DESCRIPTION.md
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_repair_order_template.py
|               |   |-- views/
|               |   |   `-- fsm_template.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_route/
|               |   |-- data/
|               |   |   |-- fsm_route_day_data.xml
|               |   |   |-- fsm_stage_data.xml
|               |   |   `-- ir_sequence.xml
|               |   |-- i18n/
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- es_CL.po
|               |   |   |-- fieldservice_route.pot
|               |   |   |-- it.po
|               |   |   |-- pt_BR.po
|               |   |   |-- pt_PT.po
|               |   |   `-- tr.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_location.py
|               |   |   |-- fsm_order.py
|               |   |   |-- fsm_route.py
|               |   |   |-- fsm_route_day.py
|               |   |   |-- fsm_route_dayroute.py
|               |   |   `-- fsm_stage.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- CREDITS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   `-- USAGE.md
|               |   |-- security/
|               |   |   `-- ir.model.access.csv
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       |-- icon.svg
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fsm_order.py
|               |   |-- views/
|               |   |   |-- fsm_location.xml
|               |   |   |-- fsm_order.xml
|               |   |   |-- fsm_route.xml
|               |   |   |-- fsm_route_day.xml
|               |   |   |-- fsm_route_dayroute.xml
|               |   |   `-- menu.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_route_availability/
|               |   |-- i18n/
|               |   |   |-- ca.po
|               |   |   |-- es.po
|               |   |   |-- fieldservice_route_availability.pot
|               |   |   |-- it.po
|               |   |   `-- pt_BR.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_blackout_day.py
|               |   |   |-- fsm_order.py
|               |   |   `-- fsm_route.py
|               |   |-- readme/
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   `-- USAGE.md
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_route_availability.py
|               |   |-- views/
|               |   |   |-- fsm_blackout_day_templates.xml
|               |   |   `-- fsm_route.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_sale/
|               |   |-- i18n/
|               |   |   |-- de.po
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- es_CL.po
|               |   |   |-- fieldservice_sale.pot
|               |   |   |-- it.po
|               |   |   |-- pt_BR.po
|               |   |   `-- sk.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_order.py
|               |   |   |-- product_template.py
|               |   |   |-- sale_order.py
|               |   |   `-- sale_order_line.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   |-- INSTALL.md
|               |   |   |-- ROADMAP.md
|               |   |   `-- USAGE.md
|               |   |-- security/
|               |   |   |-- ir.model.access.csv
|               |   |   `-- res_groups.xml
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   |-- test_fsm_sale_autofill_location.py
|               |   |   |-- test_fsm_sale_common.py
|               |   |   `-- test_fsm_sale_order.py
|               |   |-- views/
|               |   |   |-- fsm_location.xml
|               |   |   |-- fsm_order.xml
|               |   |   |-- product_template.xml
|               |   |   `-- sale_order.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_sale_agreement/
|               |   |-- i18n/
|               |   |   |-- fieldservice_sale_agreement.pot
|               |   |   `-- it.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   `-- sale_order.py
|               |   |-- readme/
|               |   |   |-- CONTRIBUTORS.md
|               |   |   `-- DESCRIPTION.md
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fsm_sale_agreement.py
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_sale_agreement_equipment_stock/
|               |   |-- i18n/
|               |   |   |-- fieldservice_sale_agreement_equipment_stock.pot
|               |   |   `-- it.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   `-- stock_move.py
|               |   |-- readme/
|               |   |   |-- CONTRIBUTORS.md
|               |   |   `-- DESCRIPTION.md
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fsm_sale_agreement_equipment_stock.py
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_sale_recurring/
|               |   |-- i18n/
|               |   |   |-- de.po
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- es_CL.po
|               |   |   |-- fieldservice_sale_recurring.pot
|               |   |   |-- fr.po
|               |   |   |-- it.po
|               |   |   `-- pt_BR.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_recurring.py
|               |   |   |-- product_template.py
|               |   |   |-- sale_order.py
|               |   |   `-- sale_order_line.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   |-- ROADMAP.md
|               |   |   `-- USAGE.md
|               |   |-- security/
|               |   |   `-- ir.model.access.csv
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       |-- icon.svg
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fsm_sale_recurring.py
|               |   |-- views/
|               |   |   |-- fsm_recurring.xml
|               |   |   |-- product_template.xml
|               |   |   `-- sale_order.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_sale_recurring_agreement/
|               |   |-- i18n/
|               |   |   |-- fieldservice_sale_recurring_agreement.pot
|               |   |   `-- it.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_recurring.py
|               |   |   `-- sale_order_line.py
|               |   |-- readme/
|               |   |   |-- CONTRIBUTORS.md
|               |   |   `-- DESCRIPTION.md
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- views/
|               |   |   `-- fsm_recurring.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_sale_stock/
|               |   |-- i18n/
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- es_CL.po
|               |   |   |-- fieldservice_sale_stock.pot
|               |   |   |-- it.po
|               |   |   `-- pt_BR.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   `-- sale_order.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   |-- ROADMAP.md
|               |   |   `-- USAGE.md
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       |-- icon.svg
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fsm_sale_order.py
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_size/
|               |   |-- i18n/
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- fieldservice_size.pot
|               |   |   |-- it.po
|               |   |   `-- pt_BR.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_location.py
|               |   |   |-- fsm_location_size.py
|               |   |   |-- fsm_order.py
|               |   |   `-- fsm_size.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   |-- ROADMAP.md
|               |   |   `-- USAGE.md
|               |   |-- security/
|               |   |   `-- ir.model.access.csv
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       |-- icon.svg
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fsm_order.py
|               |   |-- views/
|               |   |   |-- fsm_location.xml
|               |   |   |-- fsm_order.xml
|               |   |   |-- fsm_size.xml
|               |   |   `-- menu.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_skill/
|               |   |-- i18n/
|               |   |   |-- de.po
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- es_CL.po
|               |   |   |-- fieldservice_skill.pot
|               |   |   |-- it.po
|               |   |   `-- pt_BR.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_category.py
|               |   |   |-- fsm_order.py
|               |   |   |-- fsm_person.py
|               |   |   |-- fsm_person_skill.py
|               |   |   |-- fsm_template.py
|               |   |   `-- hr_skill.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- CREDITS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   |-- ROADMAP.md
|               |   |   `-- USAGE.md
|               |   |-- security/
|               |   |   `-- ir.model.access.csv
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fsm_skill.py
|               |   |-- views/
|               |   |   |-- fsm_category.xml
|               |   |   |-- fsm_order.xml
|               |   |   |-- fsm_person.xml
|               |   |   |-- fsm_person_skill.xml
|               |   |   |-- fsm_template.xml
|               |   |   `-- hr_skill.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_stage_server_action/
|               |   |-- data/
|               |   |   |-- base_automation.xml
|               |   |   |-- fsm_stage.xml
|               |   |   `-- ir_server_action.xml
|               |   |-- i18n/
|               |   |   |-- de.po
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- es_CL.po
|               |   |   |-- fieldservice_stage_server_action.pot
|               |   |   |-- it.po
|               |   |   `-- pt_BR.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_order.py
|               |   |   `-- fsm_stage.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   `-- USAGE.md
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       |-- icon.svg
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fsm_order_run_action.py
|               |   |-- views/
|               |   |   `-- fsm_stage.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_stock/
|               |   |-- data/
|               |   |   `-- fsm_stock_data.xml
|               |   |-- i18n/
|               |   |   |-- de.po
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- es_CL.po
|               |   |   |-- fieldservice_stock.pot
|               |   |   |-- fr.po
|               |   |   |-- it.po
|               |   |   `-- pt_BR.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_location.py
|               |   |   |-- fsm_order.py
|               |   |   |-- fsm_wizard.py
|               |   |   |-- procurement_group.py
|               |   |   |-- res_territory.py
|               |   |   |-- stock_move.py
|               |   |   |-- stock_picking.py
|               |   |   `-- stock_rule.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- CREDITS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   |-- INSTALL.md
|               |   |   |-- ROADMAP.md
|               |   |   `-- USAGE.md
|               |   |-- security/
|               |   |   `-- ir.model.access.csv
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       |-- icon.svg
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   |-- test_fsm_stock.py
|               |   |   `-- test_fsm_wizard.py
|               |   |-- views/
|               |   |   |-- fsm_location.xml
|               |   |   |-- fsm_order.xml
|               |   |   |-- res_territory.xml
|               |   |   |-- stock.xml
|               |   |   `-- stock_picking.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- hooks.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_timesheet/
|               |   |-- i18n/
|               |   |   |-- fieldservice_timesheet.pot
|               |   |   `-- it.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_order.py
|               |   |   `-- hr_timesheet.py
|               |   |-- readme/
|               |   |   |-- CONTRIBUTORS.md
|               |   |   `-- DESCRIPTION.md
|               |   |-- report/
|               |   |   |-- __init__.py
|               |   |   |-- report_timesheet_templates.xml
|               |   |   `-- timesheets_analysis_report.py
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- views/
|               |   |   |-- fsm_order.xml
|               |   |   `-- hr_timesheet.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- fieldservice_vehicle/
|               |   |-- i18n/
|               |   |   |-- de.po
|               |   |   |-- es.po
|               |   |   |-- es_AR.po
|               |   |   |-- es_CL.po
|               |   |   |-- fieldservice_vehicle.pot
|               |   |   |-- it.po
|               |   |   `-- pt_BR.po
|               |   |-- models/
|               |   |   |-- __init__.py
|               |   |   |-- fsm_order.py
|               |   |   |-- fsm_person.py
|               |   |   `-- fsm_vehicle.py
|               |   |-- readme/
|               |   |   |-- CONFIGURE.md
|               |   |   |-- CONTRIBUTORS.md
|               |   |   |-- CREDITS.md
|               |   |   |-- DESCRIPTION.md
|               |   |   |-- INSTALL.md
|               |   |   |-- ROADMAP.md
|               |   |   `-- USAGE.md
|               |   |-- security/
|               |   |   |-- ir.model.access.csv
|               |   |   `-- res_groups.xml
|               |   |-- static/
|               |   |   `-- description/
|               |   |       |-- icon.png
|               |   |       `-- index.html
|               |   |-- tests/
|               |   |   |-- __init__.py
|               |   |   `-- test_fsm_vehicle.py
|               |   |-- views/
|               |   |   |-- fsm_order.xml
|               |   |   |-- fsm_person.xml
|               |   |   |-- fsm_vehicle.xml
|               |   |   `-- menu.xml
|               |   |-- __init__.py
|               |   |-- __manifest__.py
|               |   |-- pyproject.toml
|               |   `-- README.rst
|               |-- setup/
|               |   `-- _metapackage/
|               |       `-- pyproject.toml
|               |-- checklog-odoo.cfg
|               |-- eslint.config.cjs
|               |-- LICENSE
|               |-- prettier.config.cjs
|               `-- README.md
|-- docker/
|   |-- odoo18/
|   |   |-- docker-compose.odoo18.yml
|   |   `-- odoo.conf
|   `-- odoo19/
|       `-- docker-compose.odoo19.yml
|-- docs/
|   |-- phase0/
|   |   |-- archive/
|   |   |   `-- 2026-01-02/
|   |   |       |-- docs-phase0-tasks.md
|   |   |       `-- itad-core-tasks.md
|   |   |-- verification_runs/
|   |   |   `-- 2026-01-02_2112.txt
|   |   |-- glossary.md
|   |   |-- object_map.md
|   |   |-- PHASE_0.md
|   |   |-- PHASE_0_EVIDENCE_INDEX.md
|   |   |-- PHASE_0_LOCK_REVIEW.md
|   |   |-- PHASE_0_RISK_REGISTER.md
|   |   |-- PHASE_0_SIGNOFF_SUMMARY.md
|   |   |-- PHASE_0_VERIFICATION_LOG.md
|   |   |-- PHASE_1_READINESS_GATE.md
|   |   `-- SOR_LOCK.md
|   |-- phase1/
|   |   |-- sample_payloads/
|   |   |   |-- pickup_manifest_forbidden_fields.json
|   |   |   `-- pickup_manifest_min.json
|   |   |-- INTEGRATION_CONTRACT_ODoo_ITADCore.md
|   |   |-- PHASE_1_CLOSURE_SUMMARY.md
|   |   |-- PHASE_1_VERIFICATION_LOG.md
|   |   |-- PHASE_1_VERIFICATION_RUN.md
|   |   |-- PRE_GOVERNANCE_EVIDENCE.md
|   |   |-- RISK_REGISTER_PHASE1.md
|   |   |-- SOR_INVARIANT_GREPS.md
|   |   |-- UI_VERTICAL_SLICE_SMOKE.md
|   |   `-- vertica_slice.md
|   |-- phase2/
|   |   |-- config_defaults.md
|   |   |-- Phase 2_Digital_Taxonomy.md
|   |   |-- PHASE_2_2_SUMMARY.md
|   |   |-- PHASE_2_2a_TASKS.md
|   |   `-- troubleshooting_receiving.md
|   |-- BATTERY PROCESSING & AGGREGATION LEAD.pdf
|   |-- Categories ROMS.xlsx
|   |-- E-WASTE MANAGER (LEAD).pdf
|   |-- IT SUPPORT & SALES.pdf
|   |-- ITAD Data Model v0.9 1.2.pdf
|   |-- MODERN WASTE SOLUTIONS â€” OPERATION FLOW.pdf
|   |-- ModernWaste_Phase1_Blueprint_Consolidation.docx
|   |-- Phase 0 Lock Review â€” Checklist (30 .pdf
|   |-- RACI Matrix Phase 0 Completion .pdf
|   |-- ROADMAP.md
|   |-- SHIPPING & RECEIVING MANAGER - copy.pdf
|   `-- SHIPPING & RECEIVING MANAGER.pdf
|-- itad-core/
|   |-- alembic/
|   |   |-- versions/
|   |   |   |-- 0001_init.sqlalchemy.py
|   |   |   |-- 0002_phase0_b.sqlalchemy.py
|   |   |   |-- 0003_phase0_c.sqlalchemy.py
|   |   |   |-- 0004_phase0_d.sqlalchemy.py
|   |   |   |-- 0005_phase0_d_receiving_constraints.sqlalchemy.py
|   |   |   |-- 0006_phase0_e_taxonomy_processing.sqlalchemy.py
|   |   |   |-- 0007_phase0_f_reconciliation_disputes.sqlalchemy.py
|   |   |   |-- 0008_phase0_g_evidence_custody.sqlalchemy.py
|   |   |   |-- 0009_phase0_h_inventory_outbound_downstream.sqlalchemy.py
|   |   |   |-- 0010_phase0_i_pickup_manifest_bridge.sqlalchemy.py
|   |   |   `-- 0011_phase0_j_pricing_placeholders_settlement_snapshot.sqlalchemy.py
|   |   `-- env.py
|   |-- app/
|   |   |-- api/
|   |   |   |-- v1/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- bol.py
|   |   |   |   |-- material_types.py
|   |   |   |   |-- pickup_manifests.py
|   |   |   |   |-- processing.py
|   |   |   |   |-- receiving.py
|   |   |   |   |-- taxonomy.py
|   |   |   |   `-- workstreams.py
|   |   |   `-- __init__.py
|   |   |-- core/
|   |   |   |-- config.py
|   |   |   |-- correlation.py
|   |   |   |-- database.py
|   |   |   |-- db.py
|   |   |   `-- idempotency.py
|   |   |-- models/
|   |   |   |-- __init__.py
|   |   |   |-- base.py
|   |   |   |-- bol.py
|   |   |   |-- bol_stage_gates.py
|   |   |   |-- domain_events.py
|   |   |   |-- evidence.py
|   |   |   |-- external_ids.py
|   |   |   |-- idempotency_keys.py
|   |   |   |-- inventory.py
|   |   |   |-- material_type.py
|   |   |   |-- pickup_manifest.py
|   |   |   |-- pricing.py
|   |   |   |-- processing.py
|   |   |   |-- receiving.py
|   |   |   |-- receiving_record_voids.py
|   |   |   |-- reconciliation.py
|   |   |   |-- settlement.py
|   |   |   |-- taxonomy.py
|   |   |   |-- workstream_stage_gates.py
|   |   |   `-- workstreams.py
|   |   |-- repositories/
|   |   |   |-- __init__.py
|   |   |   |-- artifacts_repo.py
|   |   |   |-- custody_repo.py
|   |   |   |-- discrepancy_repo.py
|   |   |   |-- downstream_repo.py
|   |   |   |-- geocode_repo.py
|   |   |   |-- inventory_repo.py
|   |   |   |-- outbound_repo.py
|   |   |   |-- pickup_manifest_repo.py
|   |   |   |-- pricing_repo.py
|   |   |   |-- reconciliation_repo.py
|   |   |   `-- settlement_repo.py
|   |   |-- schemas/
|   |   |   |-- __init__.py
|   |   |   |-- bol.py
|   |   |   |-- material_type.py
|   |   |   |-- pickup_manifest.py
|   |   |   |-- processing.py
|   |   |   |-- receiving.py
|   |   |   `-- taxonomy.py
|   |   |-- scripts/
|   |   |   `-- seed_demo.py
|   |   |-- services/
|   |   |   |-- __init__.py
|   |   |   |-- bol_service.py
|   |   |   |-- pickup_manifest_service.py
|   |   |   |-- processing_service.py
|   |   |   |-- receiving_service.py
|   |   |   `-- taxonomy_service.py
|   |   |-- __init__.py
|   |   `-- main.py
|   |-- scripts/
|   |   `-- seed_demo.py
|   |-- tests/
|   |   |-- conftest.py
|   |   |-- test_bol.py
|   |   |-- test_http_guard.py
|   |   |-- test_material_types.py
|   |   |-- test_phase0_f_reconciliation_disputes_data_layer.py
|   |   |-- test_phase0_g_evidence_custody_data_layer.py
|   |   |-- test_phase0_h_inventory_outbound_downstream_data_layer.py
|   |   |-- test_phase0_i_pickup_manifest_bridge_data_layer.py
|   |   |-- test_phase0_j_pricing_settlement_snapshot_data_layer.py
|   |   |-- test_phase1_sor_invariants.py
|   |   |-- test_phase1_vertical_slice_submit.py
|   |   |-- test_pickup_manifest_submit_contract.py
|   |   |-- test_processing_taxonomy.py
|   |   |-- test_receiving.py
|   |   `-- test_sor_guard_snapshot_exemptions.py
|   |-- alembic.ini
|   |-- docker-compose.itad-core.yml
|   |-- Dockerfile
|   |-- pyproject.toml
|   `-- README.md
|-- scripts/
|   |-- docs/
|   |   `-- phase0/
|   |       `-- verification_runs/
|   |           `-- 2026-01-02_2112.txt
|   |-- api_healthcheck.sh
|   |-- migrate_phase2.1_to_2.2.py
|   |-- phase0_sor_guard.ps1
|   |-- phase0_validate_evidence_index.py
|   |-- phase0_verify.ps1
|   |-- run_phase1_verification.ps1
|   `-- verify_phase2_2.ps1
|-- CODEX_CHECKLIST.md
|-- implementation_plan.md
|-- manifest.md
|-- Noteï€º
|-- README.md
|-- README_STRUCTURE.md
`-- tasks.md
```

## 📦 Key Components

- `itad-core/`: FastAPI service for the ITAD Core backend.
- `itad-core/app/`: Main application package.
- `itad-core/app/core/`: Configuration, database, and shared infrastructure code.
- `itad-core/app/models/`: SQLAlchemy ORM models (DB schema).
- `itad-core/app/schemas/`: Pydantic schemas for request/response validation.
- `itad-core/app/api/`: FastAPI routers grouped by resource/version.
- `itad-core/app/services/`: Business logic and orchestration layer.
- `itad-core/app/repositories/`: Data access layer (queries/CRUD).
- `itad-core/alembic/`: Database migrations.
- `itad-core/tests/`: Pytest suite and fixtures.
- `addons/common/itad_core/`: Custom Odoo module for ITAD Core integration.
- `addons/common/itad_core/models/`: Odoo models (ORM layer).
- `addons/common/itad_core/controllers/`: Odoo HTTP controllers.
- `addons/common/itad_core/views/`: Odoo UI views and templates.
- `addons/common/itad_core/data/`: Odoo data files (cron, params, demo).
- `addons/common/itad_core/security/`: Odoo access rules and groups.
- `addons/odoo18/oca/field-service/`: Vendored OCA Field Service addons (third-party).
- `docker/`: Docker configs for Odoo and related services.
- `docs/`: Project documentation and reference PDFs.
- `scripts/`: Ops/verification scripts.


## ⚙️ Configuration Files

- `itad-core/pyproject.toml`: Python project metadata and dependencies.
- `itad-core/alembic.ini`: Alembic migration configuration.
- `itad-core/Dockerfile`: Container image for the ITAD Core service.
- `itad-core/docker-compose.itad-core.yml`: Local stack for ITAD Core.
- `docker/odoo18/docker-compose.odoo18.yml`: Odoo 18 docker compose.
- `docker/odoo18/odoo.conf`: Odoo configuration file.
- `addons/common/itad_core/__manifest__.py`: Odoo module manifest.
- `addons/odoo18/oca/field-service/*/__manifest__.py`: Odoo manifests for OCA Field Service modules.
- `manifest.md`: High-level project manifest.
- `implementation_plan.md`: Delivery plan and milestones.
- `CODEX_CHECKLIST.md`: Internal checklist for Codex workflow.


## 🧩 Modules Overview (if applicable)

| Module | Purpose | Depends on |
| --- | --- | --- |
| `base_territory` | This module allows you to define territories, branches, districts and regions to be used for Field Service operations or Sales. | base |
| `fieldservice` | Manage Field Service Locations, Workers and Orders | base_territory, base_geolocalize, resource, contacts |
| `fieldservice_account` | Track invoices linked to Field Service orders | fieldservice, account |
| `fieldservice_activity` | Field Service Activities are a set of actions that need to be performed on a service order | fieldservice |
| `fieldservice_agreement` | Manage Field Service agreements and contracts | fieldservice, agreement |
| `fieldservice_availability` | Provides models for defining blackout days, stress days, and delivery time ranges for FSM availability management. | fieldservice_route |
| `fieldservice_calendar` | Add calendar to FSM Orders | calendar, fieldservice |
| `fieldservice_crm` | Create Field Service orders from the CRM | fieldservice, crm |
| `fieldservice_equipment_stock` | Integrate stock operations with your field service equipments | fieldservice_stock |
| `fieldservice_equipment_warranty` | Field Service equipment warranty | product_warranty, fieldservice_equipment_stock |
| `fieldservice_kanban_info` | Display key service information on Field Service Kanban cards. | fieldservice |
| `fieldservice_portal` | Bridge module between fieldservice and portal. | fieldservice, portal |
| `fieldservice_project` | Create field service orders from a project or project task | fieldservice, project |
| `fieldservice_recurring` | Manage recurring Field Service orders | fieldservice |
| `fieldservice_repair` | Integrate Field Service orders with MRP repair orders | repair, fieldservice_equipment_stock |
| `fieldservice_repair_order_template` | Use Repair Order Templates when creating a repair orders | fieldservice_repair, repair_order_template |
| `fieldservice_route` | Organize the routes of each day. | fieldservice |
| `fieldservice_route_availability` | Restricts blackout days for Scheduled Start (ETA) orders with the same date. | fieldservice_availability |
| `fieldservice_sale` | Sell field services. | fieldservice, sale_management, fieldservice_account |
| `fieldservice_sale_agreement` | Integrate Field Service with Sale Agreements | fieldservice_agreement, fieldservice_sale, agreement_sale |
| `fieldservice_sale_agreement_equipment_stock` | Integrate Field Service with Sale Agreements and Stock Equipment | agreement_sale, fieldservice_agreement, fieldservice_sale, fieldservice_equipment_stock, sale_stock |
| `fieldservice_sale_recurring` | Sell recurring field services. | fieldservice_recurring, fieldservice_sale, fieldservice_account |
| `fieldservice_sale_recurring_agreement` | Field Service Recurring Agreement | agreement_sale, fieldservice_agreement, fieldservice_sale_recurring |
| `fieldservice_sale_stock` | Sell stockable items linked to field service orders. | fieldservice_sale, fieldservice_stock |
| `fieldservice_size` | Manage Sizes for Field Service Locations and Orders | fieldservice, uom |
| `fieldservice_skill` | Manage your Field Service workers skills | hr_skills, fieldservice |
| `fieldservice_stage_server_action` | Execute server actions when reaching a Field Service stage | fieldservice, base_automation |
| `fieldservice_stock` | Integrate the logistics operations with Field Service | fieldservice, stock |
| `fieldservice_timesheet` | Timesheet on Field Service Orders | hr_timesheet, fieldservice_project |
| `fieldservice_vehicle` | Manage Field Service vehicles and assign drivers | fieldservice |
| `itad_core` | Odoo 18 Field Service → ITAD Core pickup_manifest + receiving confirmation with hardening | base, fieldservice |


## 📝 Notes

- Directory tree generated from file list; hidden folders and empty directories may not appear.
- The OCA Field Service subtree is vendored; treat as external dependency unless explicitly modifying vendor code.
- Database credentials and runtime settings are pulled from configuration in `itad-core/app/core/config.py`.

