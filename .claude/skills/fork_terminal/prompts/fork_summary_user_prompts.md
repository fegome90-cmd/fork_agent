# Prompt

## History

Esta es la historia de la conversacion entre el usuario y el agente.
Toma esto y usalo para entender la siguiente solicitud del usuario. Incluye versiones resumidas de tu conversacion con el usuario. De esta manera nuestros fork agents tienen una historia de conversacion y pueden entender mejor la solicitud del usuario.

`


´´´ yaml
- history:
    - user_prompt_summary: <user prompt summary>
      agent_response_summary: <agent response summary>
    - user_prompt: <user prompt>
      agent_response: <agent response>
    - user_prompt: <user prompt>
      agent_response: <agent response>

´´´


## Next User Request

<fill in the user prompt here for the fork terminal agent>