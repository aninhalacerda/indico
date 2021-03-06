<%page args="participant, conference"/>
<% from MaKaC.common.timezoneUtils import nowutc %>
<tr id="participant${participant.getId()}">
    <td class="CRLabstractDataCell" width="3%" valign="top" align="right">
        <input type="checkbox" name="participants" id="checkParticipant${participant.getId()}" value="${participant.getId()}"/>
    </td>
    <td class="CRLabstractDataCell" valign="top" id="nameParticipant${participant.getId()}">
        <a href="#" id="participantEdit${participant.getId()}">${participant.getName()}</a>
    </td>
    <td class="CRLabstractDataCell" valign="top" id="affilitationParticipant${participant.getId()}">${participant.getAffiliation()}</td>
    <td class="CRLabstractDataCell" valign="top" id="emailParticipant${participant.getId()}">${participant.getEmail()}</td>
    <td class="CRLabstractDataCell" valign="top" id="addressParticipant${participant.getId()}">${participant.getAddress()}</td>
    <td class="CRLabstractDataCell" valign="top" id="phoneParticipant${participant.getId()}">${participant.getTelephone()}</td>
    <td class="CRLabstractDataCell" valign="top" id="faxParticipant${participant.getId()}">${participant.getFax()}</td>
    <td class="CRLabstractDataCell" valign="top" id="statusParticipant${participant.getId()}">${participant.getStatus()}</td>
    <td class="CRLabstractDataCell" valign="top" id="presence${participant.getId()}">${(_("present") if participant.isPresent() else _("absent")) if nowutc() > conference.getStartDate() else "n/a"}</td>
</tr>
<script type="text/javascript">
    $('#participantEdit${participant.getId()}').click(function(){
        var onSuccess = function(result){
            $('#participant${participant.getId()}').replaceWith(result);
            $('#participant${participant.getId()}').effect("highlight",{}, 1500);
            actionParticipantRows();
        };
        var userData = {};
        userData["id"] = '${participant.getId()}';
        userData["title"] = '${participant.getTitle()}';
        userData["surName"] = '${participant.getFamilyName()}';
        userData["name"] = '${participant.getFirstName()}';
        userData["email"] = '${participant.getEmail()}';
        userData["address"] = '${participant.getAddress()}';
        userData["affiliation"] = '${participant.getAffiliation()}';
        userData["phone"] = '${participant.getTelephone()}';
        userData["fax"] = '${participant.getFax()}';
        new ApplyForParticipationPopup('${self_._conf.getId()}','event.participation.editParticipant',  $T('Edit participant'), userData, onSuccess, true);
    });
</script>
