# -*- coding: utf-8 -*-
##
##
## This file is part of Indico.
## Copyright (C) 2002 - 2012 European Organization for Nuclear Research (CERN).
##
## Indico is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 3 of the
## License, or (at your option) any later version.
##
## Indico is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Indico;if not, see <http://www.gnu.org/licenses/>.

from MaKaC.webinterface.rh.conferenceDisplay import RHConferenceBaseDisplay
import MaKaC.webinterface.urlHandlers as urlHandlers
import MaKaC.webinterface.pages.registrationForm as registrationForm
from MaKaC import registration
from MaKaC.errors import FormValuesError,MaKaCError, AccessError
from MaKaC.common import Config
from MaKaC.user import AvatarHolder
from MaKaC.webinterface.rh.registrantsModif import RHRegistrantListModif

from MaKaC.authentication import AuthenticatorMgr
from MaKaC.common.mail import GenericMailer
from MaKaC.common.utils import validMail


class RHBaseRegistrationForm( RHConferenceBaseDisplay ):

    def _checkParams( self, params ):
        RHConferenceBaseDisplay._checkParams(self, params)
        self._regForm = self._conf.getRegistrationForm()

    def _processIfActive( self ):
        """only override this method if the RegForm must be activated for
            carrying on the handler execution"""
        return "regForm"

    def _process( self ):
        #if the RegForm is not activated we show up a form informing about that.
        #   This must be done at RH level because there can be some RH not
        #   displaying pages.
        if not self._regForm.isActivated() or not self._conf.hasEnabledSection("regForm"):
            p = registrationForm.WPRegFormInactive( self, self._conf )
            return p.display()
        else:
            return self._processIfActive()


class RHRegistrationForm( RHBaseRegistrationForm ):
    _uh = urlHandlers.UHConfRegistrationForm

    def _processIfActive( self ):
        p = registrationForm.WPRegistrationForm(self, self._conf)
        return p.display()

class RHRegistrationFormSignIn( RHBaseRegistrationForm ):
    _uh = urlHandlers.UHConfRegistrationFormSignIn
    _tohttps = True

    def _checkParams( self, params ):
        RHBaseRegistrationForm._checkParams( self, params )
        self._returnURL = params.get( "returnURL", "").strip()
        if self._returnURL == "":
            self._returnURL = urlHandlers.UHConferenceDisplay.getURL( self._conf )


    def _processIfActive( self ):
        #Check for automatic login
        auth = AuthenticatorMgr()
        av = auth.autoLogin(self)
        if av:
            url = self._returnURL
            self._getSession().setUser( av )
            if Config.getInstance().getBaseSecureURL().startswith('https://'):
                url = str(url).replace('http://', 'https://')
            self._redirect( url )
        p = registrationForm.WPRegistrationFormSignIn(self, self._conf)
        return p.display()

class RHRegistrationFormDisplayBase( RHBaseRegistrationForm ):
    _uh = urlHandlers.UHConfRegistrationFormDisplay

    def _getLoginURL( self ):
        url = self.getCurrentURL()
        if url == "":
            url = urlHandlers.UHWelcome.getURL()
        urlLogin = str(urlHandlers.UHConfRegistrationFormSignIn.getURL( self._conf, url ))
        if Config.getInstance().getLoginURL().startswith("https"):
            urlLogin = urlLogin.replace("http://", "https://")
        return urlLogin


    def _checkProtection( self ):
        RHBaseRegistrationForm._checkProtection(self)
        if self._regForm.inRegistrationPeriod() and self._regForm.isMandatoryAccount() and self._getUser() == None:
            self._redirect( self._getLoginURL() )
            self._doProcess = False

class RHRegistrationFormDisplay( RHRegistrationFormDisplayBase ):
    _uh = urlHandlers.UHConfRegistrationFormDisplay

    def _processIfActive( self ):
        if self._getUser() is not None and self._getUser().isRegisteredInConf(self._conf):
            p = registrationForm.WPRegistrationFormAlreadyRegistered(self, self._conf)
        else:
            if self._conf.getRegistrationForm().isFull():
                p = registrationForm.WPRegistrationFormFull(self, self._conf)
            elif not self._conf.getRegistrationForm().inRegistrationPeriod():
                p = registrationForm.WPRegistrationFormClosed(self, self._conf)
            else:
                p = registrationForm.WPRegistrationFormDisplay(self, self._conf)
        return p.display()

class RHRegistrationFormCreation( RHRegistrationFormDisplayBase ):
    _uh = urlHandlers.UHConfRegistrationFormDisplay

    def _checkParams( self, params ):
        RHBaseRegistrationForm._checkParams(self, params)
        self._regForm = self._conf.getRegistrationForm()
        # SESSIONS
        sessionForm = self._regForm.getSessionsForm()
        sessions = sessionForm.getSessionsFromParams(params)
        params["sessions"] = sessions
        # ACCMMODATION
        params["accommodationType"] = self._regForm.getAccommodationForm().getAccommodationTypeById(params.get("accommodationType", ""))
        # SOCIAL EVENTS
        socialEventIds = self._normaliseListParam(params.get("socialEvents", []))
        se = []
        for id in socialEventIds:
            se.append(self._regForm.getSocialEventForm().getSocialEventById(id))
        params["socialEvents"] = se

    def _process( self ):
        canManageRegistration = self._conf.canManageRegistration(self._getUser())
        if not canManageRegistration and not self._regForm.isActivated():
            p = registrationForm.WPRegFormInactive( self, self._conf )
            return p.display()
        params = self._getRequestParams()
        email = self._regForm.getPersonalData().getValueFromParams(params, 'email')
        if email is None:
            raise FormValuesError(_("An email address has to be set in order to make the registration in the event."))
        elif not validMail(email, False):
            raise FormValuesError(_("The given email address is not valid."))
        matchedUsers = AvatarHolder().match({"email": email}, exact=1)
        if matchedUsers:
            user = matchedUsers[0]
        else:
            user = None
        # Check if the user can register
        if not canManageRegistration: # normal user registering. Managers can.
            if self._conf.getRegistrationForm().isFull():
                self._redirect(urlHandlers.UHConfRegistrationFormDisplay.getURL(self._conf))
                return
            elif not self._conf.getRegistrationForm().inRegistrationPeriod():
                p = registrationForm.WPRegistrationFormClosed(self, self._conf)
                return p.display()
        if user is None:
            if self._conf.hasRegistrantByEmail(email):
                raise FormValuesError("There is already a user with the email \"%s\". Please choose another one"%email)
        else:
            if user.isRegisteredInConf(self._conf):
                self._redirect(urlHandlers.UHConfRegistrationForm.getURL(self._conf))
                return
            if self._conf.hasRegistrantByEmail(email):
                if canManageRegistration:
                    raise FormValuesError("There is already a user with the email \"%s\". Please choose another one"%email)
                else:
                    raise FormValuesError("You have already registered with the email address \"%s\". If you need to modify your registration, please contact the managers of the conference."%email)

        rp = registration.Registrant()
        self._conf.addRegistrant(rp)
        rp.setValues(self._getRequestParams(), user)
        rp.setSessionBillingEnabled(self._regForm.getSessionsForm().getType() != "2priorities")
        if user is not None:
            user.addRegistrant(rp)
            rp.setAvatar(user)
        # avoid multiple sending in case of db conflict
        email = self._regForm.getNotification().createEmailNewRegistrant(self._regForm, rp)
        if email:
            GenericMailer.send(email)
        if not canManageRegistration:
            self._redirect(urlHandlers.UHConfRegistrationFormCreationDone.getURL(rp))
        else:
            self._redirect(RHRegistrantListModif._uh.getURL(self._conf))
class RHRegistrationFormCreationDone( RHRegistrationFormDisplayBase ):

    def _checkParams(self, params):
        RHRegistrationFormDisplayBase._checkParams(self, params)
        self._registrant=None
        regId=params.get("registrantId",None)
        self._authkey=params.get("authkey","")
        if regId is not None:
            self._registrant=self._conf.getRegistrantById(regId)
            if self._registrant.getRandomId() != self._authkey or self._authkey == "":
                raise AccessError("You are not authorized to access this web page")

    def _processIfActive( self ):
        if self._registrant is not None:
            p = registrationForm.WPRegistrationFormCreationDone(self, self._conf, self._registrant)
            return p.display()

class RHRegistrationFormconfirmBooking( RHRegistrationFormDisplayBase ):
    _uh = urlHandlers.UHConfRegistrationFormDisplay

    def _checkParams( self, params ):
        RHBaseRegistrationForm._checkParams(self, params)

        self._registrant=None
        regId=params.get("registrantId",None)
        if regId is not None:
            self._registrant=self._conf.getRegistrantById(regId)
        self._regForm = self._conf.getRegistrationForm()
        if self._conf.getModPay().hasPaymentConditions() and params.get("conditions","false") != "on":
            raise MaKaCError("You cannot pay without accepting the conditions")
        else:
            self._getSession().setVar("conditionsAccepted","on")

    def _processIfActive( self ):
        if self._registrant is not None:
            if self._regForm.isSendReceiptEmail():
                self._regForm.getNotification().sendEmailNewRegistrantDetailsPay(self._regForm,self._registrant)
            url=urlHandlers.UHConfRegistrationFormconfirmBookingDone.getURL(self._conf)
            url.addParam("registrantId",self._registrant.getId())
            self._redirect(url)

class RHRegistrationFormconfirmBookingDone( RHRegistrationFormDisplayBase ):

    def _checkParams(self, params):
        RHRegistrationFormDisplayBase._checkParams(self, params)
        self._registrant=None
        regId=params.get("registrantId",None)
        if regId is not None:
            self._registrant=self._conf.getRegistrantById(regId)
        cond=self._getSession().getVar("conditionsAccepted")
        if cond is None:
            raise MaKaCError("You cannot pay without accepting the conditions")
        #else:
        #    self._getSession().removeVar("conditionsAccepted")


    def _processIfActive( self ):
        if self._registrant is not None:
            p = registrationForm.WPRegistrationFormconfirmBooking(self, self._conf, self._registrant)
            return p.display()


class RHRegistrationFormModify( RHRegistrationFormDisplayBase ):
    _uh = urlHandlers.UHConfRegistrationFormDisplay

    def _process( self ):
        user = self._getUser()
        canManageRegistration = self._conf.canManageRegistration(user)
        if not canManageRegistration and (not self._regForm.isActivated() or not self._conf.hasEnabledSection("regForm")):
            p = registrationForm.WPRegFormInactive( self, self._conf )
            return p.display()
        if user is not None and user.isRegisteredInConf(self._conf):
            if not self._conf.getRegistrationForm().inRegistrationPeriod() and not self._conf.getRegistrationForm().inModificationPeriod():
                p = registrationForm.WPRegistrationFormClosed(self, self._conf)
                return p.display()
            else:
                p = registrationForm.WPRegistrationFormModify(self, self._conf)
                return p.display()
        self._redirect(urlHandlers.UHConfRegistrationForm.getURL(self._conf))

class RHRegistrationFormPerformModify( RHRegistrationFormCreation ):
    _uh = urlHandlers.UHConfRegistrationFormModify

    def _process( self ):
        if self._getUser() is not None and self._getUser().isRegisteredInConf(self._conf):
            if not self._conf.getRegistrationForm().inRegistrationPeriod() and not self._conf.getRegistrationForm().inModificationPeriod():
                p = registrationForm.WPRegistrationFormClosed(self, self._conf)
                return p.display()
            else:
                rp = self._getUser().getRegistrantById(self._conf.getId())
                # check if the email is being changed by another one that already exists
                if self._getRequestParams().get("email","") != rp.getEmail() and self._conf.hasRegistrantByEmail(self._getRequestParams().get("email","")):
                    raise FormValuesError(_("There is already a user with the email \"%s\". Please choose another one")%self._getRequestParams().get("email","--no email--"))
                rp.setValues(self._getRequestParams(), self._getUser())
                self._regForm.getNotification().sendEmailModificationRegistrant(self._regForm, rp)
                if rp.doPay():
                    self._redirect(urlHandlers.UHConfRegistrationFormCreationDone.getURL(rp))
                else:
                    self._redirect(urlHandlers.UHConfRegistrationForm.getURL(self._conf))
        else:
            self._redirect(urlHandlers.UHConfRegistrationForm.getURL(self._conf))


class RHRegistrationFormConditions( RHRegistrationFormDisplayBase ):

    def _process( self ):
        p = registrationForm.WPRegistrationFormConditions(self, self._conf)
        return p.display()
