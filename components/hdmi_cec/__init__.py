import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import automation
from esphome.core import CORE
from esphome.const import CONF_ID, CONF_TRIGGER_ID, CONF_DATA, CONF_SOURCE, CONF_ADDRESS

import logging
_LOGGER = logging.getLogger(__name__)

CODEOWNERS = ["@johnboiles"]
# DEPENDENCIES = ["spi"]
IS_PLATFORM_COMPONENT = False

CONF_DESTINATION = "destination"
CONF_ON_PACKET = "on_packet"
CONF_OPCODE = "opcode"


def validate_raw_data(value):
    if isinstance(value, list):
        return cv.Schema([cv.hex_uint8_t])(value)
    raise cv.Invalid(
        "data must be a list of bytes"
    )


hdmi_cec_ns = cg.esphome_ns.namespace("hdmi_cec")
HdmiCecComponent = hdmi_cec_ns.class_("HdmiCec", cg.Component)
HdmiCecTrigger = hdmi_cec_ns.class_(
    "HdmiCecTrigger",
    automation.Trigger.template(cg.std_vector.template(cg.uint8)),
    cg.Component,
)

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(HdmiCecComponent),
        cv.Required(CONF_ADDRESS): cv.int_range(min=0, max=15),
        cv.Optional(CONF_ON_PACKET): automation.validate_automation(
            {
                cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(HdmiCecTrigger),
                cv.Optional(CONF_SOURCE): cv.int_range(min=0, max=15),
                cv.Optional(CONF_DESTINATION): cv.int_range(min=0, max=15),
                cv.Optional(CONF_OPCODE): cv.int_range(min=0, max=255),
                cv.Optional(CONF_DATA): cv.templatable(validate_raw_data),
                # cv.Optional(CONF_ON_PACKET): automation.validate_automation(
                #     {
                #         cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(HdmiCecTrigger),
                #         cv.Optional(CONF_SOURCE): cv.int_range(min=0, max=15),
                #         cv.Optional(CONF_DESTINATION): cv.int_range(min=0, max=15),
                #         cv.Optional(CONF_OPCODE): cv.int_range(min=0, max=255),
                #         cv.Optional(CONF_DATA): cv.templatable(validate_raw_data),
                #     }
                # ),

            }
        ),
    }
).extend(cv.COMPONENT_SCHEMA)


@automation.register_action(
    "hdmi_cec.send",
    hdmi_cec_ns.class_("HdmiCecSendAction", automation.Action),
    cv.maybe_simple_value(
        {
            cv.GenerateID(): cv.use_id(HdmiCecComponent),
            cv.Optional(CONF_SOURCE): cv.int_range(min=0, max=15),
            cv.Required(CONF_DESTINATION): cv.int_range(min=0, max=15),
            cv.Required(CONF_DATA): cv.templatable(validate_raw_data),
        },
        key=CONF_DATA,
    ),
)
async def hdmi_cec_action_to_code(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])

    if CONF_SOURCE in config:
        source = await cg.templatable(config[CONF_SOURCE], args, cg.uint8)
        cg.add(var.set_source(source))

    destination = await cg.templatable(config[CONF_DESTINATION], args, cg.uint8)
    cg.add(var.set_destination(destination))

    data = config[CONF_DATA]
    if isinstance(data, bytes):
        data = [int(x) for x in data]
    if cg.is_template(data):
        templ = await cg.templatable(data, args, cg.std_vector.template(cg.uint8))
        cg.add(var.set_data_template(templ))
    else:
        cg.add(var.set_data_static(data))
    return var


async def to_code(config):
    rhs = HdmiCecComponent.new()
    var = cg.Pvariable(config[CONF_ID], rhs)

    if not CORE.has_id(config[CONF_ID]):
        var = cg.new_Pvariable(config[CONF_ID], var)

    await cg.register_component(var, config)
    cg.add(var.set_address([config[CONF_ADDRESS]]))

    for conf in config.get(CONF_ON_PACKET, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)

        # Apply optional filters
        source = conf.get(CONF_SOURCE)
        if source is not None:
            cg.add(trigger.set_source(source))
        destination = conf.get(CONF_DESTINATION)
        if destination is not None:
            cg.add(trigger.set_destination(destination))
        opcode = conf.get(CONF_OPCODE)
        if opcode is not None:
            cg.add(trigger.set_opcode(opcode))
        data = conf.get(CONF_DATA)
        if data is not None:
            cg.add(trigger.set_data(data))

        await cg.register_component(trigger, conf)
        await automation.build_automation(
            trigger, [(cg.uint8, "source"), (cg.uint8, "destination"), (cg.std_vector.template(cg.uint8), "data")], conf
        )