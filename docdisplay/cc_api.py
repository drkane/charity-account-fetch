import types

from requests import Session

ENDPOINTS = {
    "SectorDataIncomeCategory": "/sectorincomecategory",
    "SectorDataOverview": "/sectoroverview",
    "SectorDataGetTopN01All": "/sectordatatop10",
    "SectorDataIncomeBand": "/sectorincomeband",
    "SectorDataGetTop10Individual": "/sectordatatop10/{listType}",
    "GetSearchCharityByRemDate": "/searchCharityRemDate/{startDate}/{endDate}",
    "GetSearchCharityByRegDate": "/searchCharityRegDate/{startDate}/{endDate}",
    "GetCharityDetailsMulti": "/charitydetailsmulti/{RegisteredNumbers}",
    "GetSearchCharityByName": "/searchCharityName/{charityname}",
    "GetCharityFinancialHistory": "/charityfinancialhistory/{RegisteredNumber}/{suffix}",
    "GetCharityAssetsLiabilities": "/charityassetsliabilities/{RegisteredNumber}/{suffix}",
    "GetCharityCioDissolution": "/ciodissolution/{RegisteredNumber}/{suffix}",
    "GetSearchCharityByRegNumber": "/charityRegNumber/{RegisteredNumber}/{suffix}",
    "GetCharityGoverningDocument": "/charitygoverningdocument/{RegisteredNumber}/{suffix}",
    "GetCharityCheckPrimaryGrants": "/checkprimarygrants/{RegisteredNumber}/{suffix}",
    "GetCharityWhoWhatHow": "/charitywhowhathow/{RegisteredNumber}/{suffix}",
    "GetCharityDetails": "/charitydetails/{RegisteredNumber}/{suffix}",
    "GetCharityTrusteeNames": "/charitytrusteenames/{RegisteredNumber}/{suffix}",
    "GetCharityGovernanceInformation": "/charitygovernanceinformation/{RegisteredNumber}/{suffix}",
    "GetCharityConstituency": "/charityconstituency/{RegisteredNumber}/{suffix}",
    "GetCharityTrusteeInformation": "/charitytrusteeinformation/{RegisteredNumber}/{suffix}",
    "GetCharityContactInformation": "/charitycontactinformation/{RegisteredNumber}/{suffix}",
    "GetCharityRegulatoryReport": "/charityregulatoryreport/{RegisteredNumber}/{suffix}",
    "GetCharityAreaOfOperation": "/charityareaofoperation/{RegisteredNumber}/{suffix}",
    "GetCharityAoORegion": "/charityaooregion/{RegisteredNumber}/{suffix}",
    "GetCharityRegistrationHistory": "/charityregistrationhistory/{RegisteredNumber}/{suffix}",
    "GetCharityAoOLocalAuthority": "/charityaoolocalauthority/{RegisteredNumber}/{suffix}",
    "GetCharityPolicyInformation": "/charitypolicyinformation/{RegisteredNumber}/{suffix}",
    "GetCharityAoOCountryContinent": "/CharityAoOCountryContinent/{RegisteredNumber}/{suffix}",
    "GetCharityOverview": "/charityoverview/{RegisteredNumber}/{suffix}",
    "GetAllCharityDetails": "/allcharitydetails/{RegisteredNumber}/{suffix}",
    "GetCharityOtherRegulators": "/CharityOtherRegulators/{RegisteredNumber}/{suffix}",
    "GetCharityAccountArInformation": "/charityaraccounts/{RegisteredNumber}/{suffix}",
    "GetCharityOtherNames": "/charityothernames/{RegisteredNumber}/{suffix}",
    "GetCharityLinkedCharities": "/linkedcharities/{RegisteredNumber}/{suffix}",
    "GetCharityLinkedCharity": "/linkedcharity/{RegisteredNumber}/{suffix}",
}


class CharityCommissionAPI:

    base_url = "https://api.charitycommission.gov.uk/register/api"

    def __init__(self, authentication_key):
        self.auth_key = authentication_key
        self.session = Session()

        for name, path in ENDPOINTS.items():
            self._add_endpoint_function(name, path)

    def _add_endpoint_function(self, name, path):
        def return_endpoint(self, **kwargs):
            # default suffix to 0 if not provided
            if "{suffix}" in path and "suffix" not in kwargs:
                kwargs["suffix"] = 0
            return self._get_request(self.base_url + path.format(**kwargs))

        meth = types.MethodType(return_endpoint, self)
        setattr(self, name, meth)

    def _auth_headers(self):
        return {
            "Cache-Control": "no-cache",
            "Ocp-Apim-Subscription-Key": self.auth_key,
        }

    def _get_request(self, url):
        r = self.session.get(url, headers=self._auth_headers())
        return r.json()

    def _post_request(self, url, data):
        r = self.session.post(url, data=data, headers=self._auth_headers())
        return r.json()
