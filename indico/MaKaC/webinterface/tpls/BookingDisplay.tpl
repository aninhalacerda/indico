<%page args="Booking=None, Kind=None, Timezone=None"/>
<% from MaKaC.common.timezoneUtils import isToday, isTomorrow, isSameDay %>

<%
id = Booking.getId()
firstLineInfo = Booking._getFirstLineInfo(Timezone)
%>

<div class="collaborationDisplayBookingLine" style="padding-left: 20px">

    <div class="collaborationConfDisplayBookingLine">
    <span class="collaborationDisplayBookingType" style="font-style:italic">
        ${ Booking._getTypeDisplayName() }
        ${":" if not Booking.getStartDate() else ""}
    </span>
    % if Booking.getStartDate():
        % if Kind == 'scheduled' and isSameDay(Booking.getStartDate(), Booking.getEndDate(), Timezone):
            <span>
            % if isToday(Booking.getStartDate(), Timezone) :
            today
            % elif isTomorrow(Booking.getStartDate(), Timezone) :
                tomorrow
            % else:
                ${ formatDate(Booking.getAdjustedStartDate(Timezone).date(), format = "%a %d/%m") }
            % endif
            </span>
            from
            ${ formatTime(Booking.getAdjustedStartDate(Timezone).time()) }
            to
            ${ formatTime(Booking.getAdjustedEndDate(Timezone).time()) }
        % else:
            % if Kind == 'scheduled' :
                from
                % if isToday(Booking.getStartDate(), Timezone) :
                    today at
                % elif isTomorrow(Booking.getStartDate(), Timezone) :
                    tomorrow at
                % else:
                    ${ formatDate(Booking.getAdjustedStartDate(Timezone).date(), format = "%a %d/%m") } at
                % endif

                ${ formatTime(Booking.getAdjustedStartDate(Timezone).time()) }

                until

            % else:
                ongoing until
            % endif



            % if isToday(Booking.getEndDate(), Timezone) :
                today at
            % elif isTomorrow(Booking.getEndDate(), Timezone) :
                tomorrow at
            % else:
                ${ formatDate(Booking.getAdjustedEndDate(Timezone).date(), format = "%a %d/%m") } at
            % endif

            ${ formatTime(Booking.getAdjustedEndDate(Timezone).time()) }
        % endif
        ${":" if firstLineInfo else "."}
    % endif

    % if firstLineInfo:
        <strong>${ firstLineInfo }</strong>
    % endif

    <% displayInfo = Booking._getInformationDisplay(Timezone) %>
    <% launchInfo = Booking._getLaunchDisplayInfo() %>

    % if displayInfo or launchInfo:
    <span style="margin-left:20px;"></span>
    % endif

    % if displayInfo:
        <span class="collaborationDisplayMoreInfo" id="collaborationBookingMoreInfo${id}">${ _("More Info") }</span>
    % endif

    % if displayInfo and ((Kind == 'ongoing' and launchInfo) or Booking.getType()=="Vidyo"):
        <span style="margin-left: 5px; margin-right:5px;">|</span>
    % endif

    % if (Kind == 'ongoing' and launchInfo) or Booking.getType()=="Vidyo":
        <a href="${ launchInfo['launchLink'] }" id="bookingLink${id}">
            ${ launchInfo['launchText'] }
        </a>
        <script type="text/javascript">
            $E('bookingLink${id}').dom.onmouseover = function (event) {
                IndicoUI.Widgets.Generic.tooltip($E('bookingLink${id}').dom, event,
                        '<div class="collaborationLinkTooltipConference">${ launchInfo["launchTooltip"] }<\/div>');
            }
        </script>
    % endif

    % if displayInfo and Booking.canBeConnected() and self_._rh._getUser() and (conf.canModify(self_._rh._aw) or Booking.getOwner()["id"] == self_._rh._getUser().getId()):
        <span style="margin-left:3px;margin-right:3px;">|</span>
        <script type="text/javascript">
          var booking${Booking.getId()} = bookings[${Booking.getId()|n,j}];
        </script>

        <a href="#" style="font-size:12px" data-booking-id="${Booking.getId()}" data-event="${conf.getId()}" class="connect_room">${_("Connect")} ${Booking.getLinkVideoRoomLocation()}</a>
        <div style="display:inline; vertical-align:middle" class="progress"></div>
        % endif

    </div>

    % if displayInfo:
        <div id="collaborationInfoLine${id}" style="visibility: hidden; overflow: hidden;">
            <div class="collaborationDisplayInfoLine">
            ${ Booking._getInformationDisplay(Timezone) }
            </div>
        </div>

        <script type="text/javascript">
            var bookingInfoState${id} = false;
            var height${id} = IndicoUI.Effect.prepareForSlide('collaborationInfoLine${id}', true);
            $E('collaborationBookingMoreInfo${id}').observeClick(function(){
                if (bookingInfoState${ Booking.getId() }) {
                    IndicoUI.Effect.slide('collaborationInfoLine${id}', height${id});
                    $E('collaborationBookingMoreInfo${id}').set($T('More info'));
                    $E('collaborationBookingMoreInfo${id}').dom.className = 'collaborationDisplayMoreInfo';
                } else {
                    IndicoUI.Effect.slide('collaborationInfoLine${id}', height${id});
                    $E('collaborationBookingMoreInfo${id}').set($T('Hide info'));
                    $E('collaborationBookingMoreInfo${id}').dom.className = 'collaborationDisplayHideInfo';
                }
                bookingInfoState${id} = !bookingInfoState${id};
            });
            $E('collaborationBookingMoreInfo${id}').dom.onmouseover = function (event) {
                IndicoUI.Widgets.Generic.tooltip($E('collaborationBookingMoreInfo${id}').dom, event,
                        '<div class="collaborationLinkTooltipConference">Click here to show / hide detailed information.<\/div>');
            }
        </script>
    % endif
</div>
